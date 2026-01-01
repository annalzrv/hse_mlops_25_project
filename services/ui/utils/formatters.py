from typing import Optional

def format_price(price: Optional[float]) -> str:
    if price is None:
        return "N/A"
    return f"${price:,.2f}"

def format_rating(rating: Optional[float]) -> str:
    if rating is None:
        return "N/A"
    return f"{rating:.2f}"

def format_coordinates(lat: Optional[float], lng: Optional[float]) -> str:
    if lat is None or lng is None:
        return "N/A"
    return f"{lat:.6f}, {lng:.6f}"
