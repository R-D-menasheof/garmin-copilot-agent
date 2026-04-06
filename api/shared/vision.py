"""Vision — SSOT for Azure OpenAI food analysis.

Handles:
- Image analysis (food photos → list of MealEntry)
- Text NLP parsing (free text → list of MealEntry)

All LLM calls go through this module. No other module should call Azure OpenAI.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openai import AzureOpenAI

from vitalis.models import MealEntry, NutritionSource

logger = logging.getLogger(__name__)


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


def _get_openai_client() -> AzureOpenAI:
    """Create Azure OpenAI client from environment variables."""
    from openai import AzureOpenAI as _AzureOpenAI

    return _AzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_KEY"],
        api_version="2024-10-21",
    )


def _get_deployment() -> str:
    """Get the Azure OpenAI deployment name."""
    return os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")


def _parse_llm_items(raw_json: str, timestamp: datetime | None = None) -> list[MealEntry]:
    """Parse LLM JSON output into MealEntry list."""
    ts = timestamp or datetime.now()
    items = json.loads(raw_json)
    result: list[MealEntry] = []
    for item in items:
        result.append(
            MealEntry(
                food_name=item["food_name"],
                calories=int(item.get("calories", 0)),
                protein_g=float(item.get("protein_g", 0)),
                carbs_g=float(item.get("carbs_g", 0)),
                fat_g=float(item.get("fat_g", 0)),
                portion_description=item.get("portion_description"),
                source=NutritionSource.LLM,
                timestamp=ts,
            )
        )
    return result


def analyze_food_image(
    image_bytes: bytes,
    timestamp: datetime | None = None,
) -> list[MealEntry]:
    """Analyze a food photo using Azure OpenAI vision.

    Args:
        image_bytes: Raw image bytes (JPEG, PNG, etc.).
        timestamp: When the meal was consumed (defaults to now).

    Returns:
        List of MealEntry objects for each detected food item.

    Raises:
        ValueError: If image_bytes is empty.
        openai.APITimeoutError: If the API call times out.
    """
    if not image_bytes:
        raise ValueError("image bytes cannot be empty")

    client = _get_openai_client()
    b64_image = base64.b64encode(image_bytes).decode()

    response = client.chat.completions.create(
        model=_get_deployment(),
        messages=[
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"},
                    },
                ],
            },
        ],
        max_completion_tokens=1000,
    )

    raw = response.choices[0].message.content
    logger.info("Vision analysis returned: %s", raw[:200])
    return _parse_llm_items(raw, timestamp)


def parse_food_text(
    text: str,
    timestamp: datetime | None = None,
) -> list[MealEntry]:
    """Parse free-text food description using Azure OpenAI NLP.

    Args:
        text: User's food description (Hebrew or English).
        timestamp: When the meal was consumed (defaults to now).

    Returns:
        List of MealEntry objects for each detected food item.

    Raises:
        openai.APITimeoutError: If the API call times out.
    """
    client = _get_openai_client()

    response = client.chat.completions.create(
        model=_get_deployment(),
        messages=[
            {"role": "system", "content": NLP_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        max_completion_tokens=1000,
    )

    raw = response.choices[0].message.content
    logger.info("NLP parsing returned: %s", raw[:200])
    return _parse_llm_items(raw, timestamp)
