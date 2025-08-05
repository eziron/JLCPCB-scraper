import unicodedata
import re

def strip_accents_and_lower(text: str) -> str:
    """
    Elimina diacríticos (tildes) y pasa la cadena a minúsculas.
    """
    if not text:
        return ""
    text_nfd = unicodedata.normalize("NFD", text)
    text_without_accents = "".join(
        c for c in text_nfd if unicodedata.category(c) != "Mn"
    )
    return text_without_accents.lower()


def clean_text_value(text) -> str:
    if not isinstance(text, str):  # Handle NaN, numbers, booleans, etc.
        return text

    try:
        # 1. Normalize to decompose combined characters (accents)
        text_nfd = unicodedata.normalize("NFD", text)
        # 2. Remove combining diacritical marks (accents)
        text_without_accents = "".join(
            c for c in text_nfd if unicodedata.category(c) != "Mn"
        )
    except TypeError:
        # In case unexpected non-string data slips through
        return text

    # 3. Convert to lowercase
    text_lower = text_without_accents.lower()

    # 4. Remove non-ASCII characters
    text_cleaned = re.sub(r"[^\x00-\x7F]+", "", text_lower)

    # 5. Normalize whitespace (replace multiple spaces/tabs/newlines with single space and strip)
    text_cleaned = re.sub(r"\s+", " ", text_cleaned).strip()

    return text_cleaned

def get_unit_price(price_tiers) -> float | None:
    if not isinstance(price_tiers, list) or not price_tiers:
        return None
    try:
        first_tier = price_tiers[0]
        if isinstance(first_tier, dict):
            price = first_tier.get("productPrice")
            return float(price) if price is not None else None
        else:
            return None
    except (IndexError, TypeError, ValueError):
        return None
    
def get_min_price(price_tiers) -> float:
        if not isinstance(price_tiers, list) or len(price_tiers) == 0: 
            return 999999
        
        min_price = 999999
        for tier in price_tiers:
            if tier and isinstance(tier, dict):
                p = tier.get("productPrice", 999999)
                if p < min_price: min_price = p
        return min_price