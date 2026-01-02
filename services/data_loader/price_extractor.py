import re
from typing import Optional

def extract_price_per_night(listing: dict) -> Optional[float]:
    """
    Extract price per night from listing.
    Handles prices that may be for multiple nights by extracting the qualifier
    and calculating price per night.
    """
    price = None
    nights = None

    # Try structuredDisplayPrice.primaryLine (at top level)
    if "structuredDisplayPrice" in listing:
        primary_line = listing.get("structuredDisplayPrice", {}).get("primaryLine", {})
        price_str = primary_line.get("price") or primary_line.get("discountedPrice") or primary_line.get("originalPrice")
        qualifier = primary_line.get("qualifier", "")

        if price_str:
            try:
                price = float(price_str.replace("$", "").replace(",", "").strip())

                # Extract number of nights from qualifier
                # Patterns: "for 5 nights", "per night", "1 night", etc.
                if qualifier:
                    nights_match = re.search(r'(\d+)\s*(?:night|nights)', qualifier, re.IGNORECASE)
                    if nights_match:
                        nights = int(nights_match.group(1))
                    elif re.search(r'per\s+night', qualifier, re.IGNORECASE):
                        nights = 1

            except (ValueError, AttributeError):
                pass

    # Fallback: try pricingQuote.structuredStayDisplayPrice.primaryLine.price
    if price is None and "pricingQuote" in listing:
        primary_line = listing.get("pricingQuote", {}).get("structuredStayDisplayPrice", {}).get("primaryLine", {})
        price_str = primary_line.get("price")
        qualifier = primary_line.get("qualifier", "")

        if price_str:
            try:
                price = float(price_str.replace("$", "").replace(",", "").strip())

                if qualifier:
                    nights_match = re.search(r'(\d+)\s*(?:night|nights)', qualifier, re.IGNORECASE)
                    if nights_match:
                        nights = int(nights_match.group(1))
                    elif re.search(r'per\s+night', qualifier, re.IGNORECASE):
                        nights = 1

            except (ValueError, AttributeError):
                pass

    # Calculate price per night
    if price is not None:
        if nights and nights > 0:
            return price / nights
        else:
            # If no qualifier or nights not found, assume price is per night
            return price

    return None

