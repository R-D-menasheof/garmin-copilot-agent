"""Food lookup — SSOT for external food database queries.

Implements the nutrition cascade pipeline:
1. Personal history (fuzzy match against known_foods cache)
2. Open Food Facts API (free, supports Hebrew)
3. USDA FoodData Central (English only)
4. Signal LLM fallback (handled by vision.py)
5. Direct entry bypass (handled by caller)
"""

from __future__ import annotations

import logging
import re

import httpx
from rapidfuzz import fuzz

from vitalis.models import KnownFood, NutritionSource

logger = logging.getLogger(__name__)

OFF_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"
OFF_BARCODE_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
USDA_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

_HTTP_TIMEOUT = 5.0


# ── Language Detection ─────────────────────────────────────────────


def detect_language(text: str) -> str:
    """Detect if text is primarily Hebrew or English.

    Hebrew characters are weighted more heavily because Hebrew is an abjad
    (consonant-only script) — fewer characters carry more meaning than Latin.

    Returns:
        "he" if any Hebrew characters are present, else "en".
    """
    hebrew_chars = len(re.findall(r"[\u0590-\u05FF]", text))
    return "he" if hebrew_chars > 0 else "en"


# ── Step 1: Personal History (Fuzzy Match) ─────────────────────────


def find_in_cache(
    query: str,
    cache: list[KnownFood],
    threshold: float = 0.8,
) -> KnownFood | None:
    """Find best fuzzy match in food cache.

    Checks food_name AND all aliases. Returns None if best score < threshold.
    """
    best_match: KnownFood | None = None
    best_score = 0.0

    for food in cache:
        score = fuzz.ratio(query.lower(), food.food_name.lower()) / 100
        if score > best_score:
            best_score = score
            best_match = food

        for alias in food.aliases:
            score = fuzz.ratio(query.lower(), alias.lower()) / 100
            if score > best_score:
                best_score = score
                best_match = food

    if best_score >= threshold and best_match is not None:
        logger.debug(
            "Cache hit: '%s' → '%s' (score=%.2f)",
            query, best_match.food_name, best_score,
        )
        return best_match
    return None


# ── Step 2: Open Food Facts ────────────────────────────────────────


async def search_open_food_facts(query: str) -> KnownFood | None:
    """Search Open Food Facts by product name.

    Args:
        query: Food name (Hebrew or English).

    Returns:
        KnownFood if found, None otherwise.
    """
    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 1,
        "fields": "product_name,nutriments",
    }
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.get(OFF_SEARCH_URL, params=params)
            if resp.status_code != 200:
                return None
            data = resp.json()
            products = data.get("products", [])
            if not products:
                return None
            return _parse_off_product(products[0])
    except (httpx.TimeoutException, httpx.HTTPError) as exc:
        logger.warning("Open Food Facts search failed: %s", exc)
        return None


async def search_open_food_facts_barcode(barcode: str) -> KnownFood | None:
    """Look up a product by barcode on Open Food Facts.

    Args:
        barcode: EAN/UPC barcode string.

    Returns:
        KnownFood if found, None otherwise.
    """
    url = OFF_BARCODE_URL.format(barcode=barcode)
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if data.get("status") != 1:
                return None
            return _parse_off_product(data["product"])
    except (httpx.TimeoutException, httpx.HTTPError) as exc:
        logger.warning("Open Food Facts barcode lookup failed: %s", exc)
        return None


def _parse_off_product(product: dict) -> KnownFood:
    """Convert an Open Food Facts product dict to KnownFood."""
    n = product.get("nutriments", {})
    return KnownFood(
        food_name=product.get("product_name", ""),
        calories_per_100g=int(n.get("energy-kcal_100g", 0)),
        protein_per_100g=float(n.get("proteins_100g", 0)),
        carbs_per_100g=float(n.get("carbohydrates_100g", 0)),
        fat_per_100g=float(n.get("fat_100g", 0)),
        fiber_per_100g=float(n.get("fiber_100g", 0)) if n.get("fiber_100g") else None,
        source=NutritionSource.OPEN_FOOD_FACTS,
    )


# ── Step 3: USDA FoodData Central ─────────────────────────────────


async def search_usda(query: str, api_key: str) -> KnownFood | None:
    """Search USDA FoodData Central. English queries only.

    Args:
        query: Food name in English.
        api_key: USDA FoodData Central API key.

    Returns:
        KnownFood if found, None otherwise.
    """
    params = {"query": query, "pageSize": 1, "api_key": api_key}
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.get(USDA_SEARCH_URL, params=params)
            if resp.status_code != 200:
                return None
            foods = resp.json().get("foods", [])
            if not foods:
                return None
            return _parse_usda_food(foods[0])
    except (httpx.TimeoutException, httpx.HTTPError) as exc:
        logger.warning("USDA search failed: %s", exc)
        return None


def _parse_usda_food(food: dict) -> KnownFood:
    """Convert a USDA food dict to KnownFood."""
    nutrients = {n["nutrientName"]: n.get("value", 0) for n in food.get("foodNutrients", [])}
    return KnownFood(
        food_name=food.get("description", ""),
        calories_per_100g=int(nutrients.get("Energy", 0)),
        protein_per_100g=float(nutrients.get("Protein", 0)),
        carbs_per_100g=float(nutrients.get("Carbohydrate, by difference", 0)),
        fat_per_100g=float(nutrients.get("Total lipid (fat)", 0)),
        fiber_per_100g=float(nutrients.get("Fiber, total dietary", 0)) or None,
        source=NutritionSource.USDA,
    )


# ── Cascade: resolve_food ──────────────────────────────────────────


async def resolve_food(
    query: str,
    cache: list[KnownFood],
    usda_api_key: str | None = None,
) -> tuple[KnownFood | None, NutritionSource]:
    """Run the full food lookup cascade.

    Returns:
        (food, source) if resolved, or (None, LLM) to signal the caller
        should invoke vision.py for LLM fallback.
    """
    # Step 1: Personal history (fuzzy match)
    cached = find_in_cache(query, cache)
    if cached:
        return cached, NutritionSource.HISTORY

    # Step 2: Open Food Facts
    off_result = await search_open_food_facts(query)
    if off_result:
        return off_result, NutritionSource.OPEN_FOOD_FACTS

    # Step 3: USDA (English only — skip for Hebrew)
    lang = detect_language(query)
    if lang == "en" and usda_api_key:
        usda_result = await search_usda(query, usda_api_key)
        if usda_result:
            return usda_result, NutritionSource.USDA

    # Step 4: Signal LLM fallback (caller invokes vision.py)
    logger.info("Cascade miss for '%s' — signaling LLM fallback", query)
    return None, NutritionSource.LLM


# ── Sync wrappers (for Azure Functions) ────────────────────────────


def search_open_food_facts_sync(query: str) -> KnownFood | None:
    """Synchronous version of search_open_food_facts."""
    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 1,
        "fields": "product_name,nutriments",
    }
    try:
        resp = httpx.get(OFF_SEARCH_URL, params=params, timeout=_HTTP_TIMEOUT)
        if resp.status_code != 200:
            return None
        data = resp.json()
        products = data.get("products", [])
        if not products:
            return None
        return _parse_off_product(products[0])
    except (httpx.TimeoutException, httpx.HTTPError) as exc:
        logger.warning("Open Food Facts search failed: %s", exc)
        return None


def search_open_food_facts_barcode_sync(barcode: str) -> KnownFood | None:
    """Synchronous barcode lookup against Open Food Facts."""
    try:
        resp = httpx.get(OFF_BARCODE_URL.format(barcode=barcode), timeout=_HTTP_TIMEOUT)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get("status") != 1:
            return None
        return _parse_off_product(data["product"])
    except (httpx.TimeoutException, httpx.HTTPError) as exc:
        logger.warning("Open Food Facts barcode lookup failed: %s", exc)
        return None


def resolve_food_sync(
    query: str,
    cache: list[KnownFood],
    usda_api_key: str | None = None,
) -> tuple[KnownFood | None, NutritionSource]:
    """Synchronous version of resolve_food — for Azure Functions."""
    # Step 1: Personal history
    cached = find_in_cache(query, cache)
    if cached:
        return cached, NutritionSource.HISTORY

    # Step 2: Open Food Facts (sync)
    off_result = search_open_food_facts_sync(query)
    if off_result:
        return off_result, NutritionSource.OPEN_FOOD_FACTS

    # Step 3: USDA (skip for Hebrew)
    lang = detect_language(query)
    if lang == "en" and usda_api_key:
        try:
            resp = httpx.get(
                USDA_SEARCH_URL,
                params={"query": query, "pageSize": 1, "api_key": usda_api_key},
                timeout=_HTTP_TIMEOUT,
            )
            if resp.status_code == 200:
                foods = resp.json().get("foods", [])
                if foods:
                    return _parse_usda_food(foods[0]), NutritionSource.USDA
        except (httpx.TimeoutException, httpx.HTTPError) as exc:
            logger.warning("USDA search failed: %s", exc)

    # Step 4: Signal LLM fallback
    logger.info("Cascade miss for '%s' — signaling LLM fallback", query)
    return None, NutritionSource.LLM
