---
name: nutrition-data-pipeline
description: "Nutrition ingestion cascade pipeline for Vitalis. Food lookup via cache → Open Food Facts → USDA → Azure OpenAI LLM. Fuzzy match with rapidfuzz, Hebrew-aware routing, Zero-Redundancy caching, image analysis prompts, NLP parsing. Use when: food lookup, cascade logic, Open Food Facts API, USDA API, LLM food analysis, barcode scan, food cache."
---

# Skill: Nutrition Data Pipeline

## Cascade Logic (FR-1.1 → FR-1.5)

When a user logs food, resolve nutritional data with minimum cost and latency:

```
User input (text / image / barcode / selection)
  │
  ▼
Step 1: Personal History (fuzzy match)
  ├── Match found (score ≥ 0.8) → Return cached KnownFood ✓
  └── No match ↓
  │
  ▼
Step 2: Open Food Facts API (free, supports Hebrew)
  ├── Found → Cache in known_foods.json → Return ✓
  └── Not found ↓
  │
  ▼
Step 3: USDA FoodData Central (English only)
  ├── Skip if input is Hebrew (detected by detect_language())
  ├── Found → Cache → Return ✓
  └── Not found ↓
  │
  ▼
Step 4: Azure OpenAI LLM (fallback — costs money)
  ├── Vision for images → Return list[MealEntry] ✓
  ├── NLP for text → Return list[MealEntry] ✓
  └── Cache resolved food in known_foods.json
  │
  ▼
Step 5: Direct Entry (FR-1.5 — bypass all above)
  └── User provides raw macros → Store as-is ✓
```

## SSOT Modules

| Module | Owns |
|--------|------|
| `api/shared/food_lookup.py` | Fuzzy match + Open Food Facts + USDA queries |
| `api/shared/vision.py` | Azure OpenAI vision + NLP calls |
| `api/shared/blob_store.py` | Food cache read/write |

## Step 1: Personal History (Fuzzy Match)

Uses `rapidfuzz` for in-memory matching against `known_foods.json`.

```python
from rapidfuzz import fuzz

def find_in_cache(
    query: str,
    cache: list[KnownFood],
    threshold: float = 0.8,
) -> KnownFood | None:
    """Find best fuzzy match in food cache.

    Checks food_name AND all aliases. Returns None if best score < threshold.
    """
    best_match = None
    best_score = 0.0

    for food in cache:
        # Check primary name
        score = fuzz.ratio(query.lower(), food.food_name.lower()) / 100
        if score > best_score:
            best_score = score
            best_match = food

        # Check aliases
        for alias in food.aliases:
            score = fuzz.ratio(query.lower(), alias.lower()) / 100
            if score > best_score:
                best_score = score
                best_match = food

    return best_match if best_score >= threshold else None
```

**Performance**: 1000 items × 3 aliases each = 4000 comparisons, <1ms on any device.

## Step 2: Open Food Facts API

Free API, supports Hebrew product names and barcodes.

```python
import httpx

OFF_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"
OFF_BARCODE_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"

async def search_open_food_facts(query: str) -> KnownFood | None:
    """Search Open Food Facts by product name."""
    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 1,
        "fields": "product_name,nutriments",
    }
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(OFF_SEARCH_URL, params=params)
        if resp.status_code != 200:
            return None
        data = resp.json()
        products = data.get("products", [])
        if not products:
            return None
        return _parse_off_product(products[0])

def _parse_off_product(product: dict) -> KnownFood:
    """Convert Open Food Facts product to KnownFood."""
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
```

## Step 3: USDA FoodData Central

Free API (requires API key), English only.

```python
USDA_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

async def search_usda(query: str, api_key: str) -> KnownFood | None:
    """Search USDA FoodData Central. English queries only."""
    params = {"query": query, "pageSize": 1, "api_key": api_key}
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(USDA_SEARCH_URL, params=params)
        if resp.status_code != 200:
            return None
        foods = resp.json().get("foods", [])
        if not foods:
            return None
        return _parse_usda_food(foods[0])
```

## Step 4: Azure OpenAI LLM

### Image Analysis Prompt (FR-1.3)

```python
VISION_SYSTEM_PROMPT = """You are a nutrition analysis assistant. Analyze the food in
this image and return a JSON array of items with their estimated nutritional values.

For each food item visible, return:
{
  "food_name": "name in the user's language",
  "calories": estimated_kcal_for_visible_portion,
  "protein_g": grams,
  "carbs_g": grams,
  "fat_g": grams,
  "portion_description": "e.g., 1 plate, ~200g"
}

Be specific about portions. If unsure, give your best estimate with a note.
Return ONLY valid JSON array, no markdown."""
```

### NLP Parsing Prompt (FR-1.4)

```python
NLP_SYSTEM_PROMPT = """You are a nutrition parser. Parse the user's food description
into structured nutrition data. The user may write in Hebrew or English.

For each food item mentioned, return:
{
  "food_name": "name as the user wrote it",
  "calories": estimated_kcal,
  "protein_g": grams,
  "carbs_g": grams,
  "fat_g": grams,
  "portion_description": "quantity and unit from the text"
}

Handle quantities: "2 תפוחים" = 2 apples, "שייק חלבון" = 1 protein shake.
If no quantity specified, assume 1 standard serving.
Return ONLY valid JSON array, no markdown."""
```

## Hebrew-Aware Routing

```python
import re

def detect_language(text: str) -> str:
    """Detect if text is primarily Hebrew or English."""
    hebrew_chars = len(re.findall(r'[\u0590-\u05FF]', text))
    latin_chars = len(re.findall(r'[a-zA-Z]', text))
    return "he" if hebrew_chars >= latin_chars else "en"
```

**Routing rule**: If `detect_language(query) == "he"`, skip USDA (no Hebrew data) and go directly to LLM after Open Food Facts miss.

## Zero-Redundancy Caching

**Goal**: <5% of meals trigger LLM calls after 1 month of use.

Every time the cascade resolves a food (from any source), the result is appended to `food_cache/known_foods.json` via `blob_store.append_food_cache()`. Next time the same food is logged, Step 1 fuzzy match finds it instantly.

Deduplication: `append_food_cache()` checks if `food_name` already exists (case-insensitive) before appending.

## Data Model

All models live in `src/vitalis/models.py` (SSOT):

- `NutritionSource` — enum: history, open_food_facts, usda, llm, manual
- `MealEntry` — food_name, calories, protein_g, carbs_g, fat_g, fiber_g, portion_description, source, timestamp
- `KnownFood` — food_name, calories_per_100g, protein_per_100g, carbs_per_100g, fat_per_100g, fiber_per_100g, source, aliases

## Full Cascade Function

```python
async def resolve_food(
    query: str,
    cache: list[KnownFood],
    usda_api_key: str | None = None,
) -> tuple[KnownFood | None, NutritionSource]:
    """Run the full cascade. Returns (food, source) or (None, None)."""

    # Step 1: Personal history
    cached = find_in_cache(query, cache)
    if cached:
        return cached, NutritionSource.HISTORY

    # Step 2: Open Food Facts
    off_result = await search_open_food_facts(query)
    if off_result:
        return off_result, NutritionSource.OPEN_FOOD_FACTS

    # Step 3: USDA (English only)
    lang = detect_language(query)
    if lang == "en" and usda_api_key:
        usda_result = await search_usda(query, usda_api_key)
        if usda_result:
            return usda_result, NutritionSource.USDA

    # Step 4: LLM (handled by caller via vision.py)
    return None, NutritionSource.LLM
```

Note: The LLM call itself is done by `vision.py` (SSOT for LLM). The cascade function returns `(None, LLM)` to signal the caller should invoke `vision.parse_food_text()`.
