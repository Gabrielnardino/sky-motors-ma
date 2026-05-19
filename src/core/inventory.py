"""
Inventory loader for Sky Motors.
Reads from data/Active Inventory.csv.
In production, swap _load_inventory() for a PostgreSQL query (see data/queries.sql).
"""
from __future__ import annotations
import csv
import io
import re
from pathlib import Path

_CSV_PATH = Path(__file__).parent.parent.parent / "data" / "Active Inventory.csv"


def _parse_price(value: str) -> int:
    """Parse a price string to int cents-less. Returns 0 on failure."""
    try:
        clean = value.strip().replace(",", "")
        f = float(clean)
        return int(f) if f > 0 else 0
    except (ValueError, TypeError):
        return 0


def _load_inventory() -> list[dict]:
    if not _CSV_PATH.exists():
        return []

    with open(_CSV_PATH, encoding="utf-8") as f:
        content = f.read()

    lines = content.splitlines()
    # Strip spaces from header column names (CSV uses "; " as separator in header)
    lines[0] = ";".join(col.strip() for col in lines[0].split(";"))

    reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter=";")
    vehicles: list[dict] = []

    for row in reader:
        # Skip sold vehicles
        if row.get("CustomStatus", "").strip().upper() == "SOLD":
            continue
        if row.get("InventoryStatus", "").strip().upper() != "IN INVENTORY":
            continue

        # Price hierarchy: AdvertisingPrice > VehiclePrice
        price = _parse_price(row.get("AdvertisingPrice", "0")) or \
                _parse_price(row.get("VehiclePrice", "0"))

        # Book values for budget matching when no price is set
        book_low  = _parse_price(row.get("BookValue2", "0"))   # floor market value
        book_high = _parse_price(row.get("BookValue3", "0"))   # high market value

        mileage     = _parse_price(row.get("Mileage", "0"))
        days_in_stock = _parse_price(row.get("DaysInStock", "0"))

        info = row.get("VehicleInfo", "").strip()
        tokens = info.split()
        year  = int(tokens[0]) if tokens and tokens[0].isdigit() else 0
        make  = tokens[1].title() if len(tokens) > 1 else ""
        model = tokens[2].title() if len(tokens) > 2 else ""

        vehicles.append({
            "stock":        row.get("StockNumber", "").strip(),
            "vin":          row.get("Vin", "").strip(),
            "description":  info,
            "year":         year,
            "make":         make,
            "model":        model,
            "color":        row.get("Color", "").strip().title(),
            "mileage":      mileage,
            "price":        price,
            "book_low":     book_low,
            "book_high":    book_high,
            "days_in_stock": days_in_stock,
            "no_price":     row.get("IsNoPrice", "False").strip() == "True",
        })

    # Priced vehicles first, then by price ascending
    vehicles.sort(key=lambda v: (v["price"] == 0, v["price"]))
    return vehicles


INVENTORY: list[dict] = _load_inventory()


def _extract_budget(text: str) -> int | None:
    """Pull the first dollar amount from a budget string, e.g. 'under $25,000' → 25000."""
    text = text.replace(",", "")
    # Handle shorthand like $25k or 25K
    text = re.sub(r"(\d+)[kK]", lambda m: str(int(m.group(1)) * 1000), text)
    match = re.search(r"\$?\s*(\d{4,6})", text)
    return int(match.group(1)) if match else None


_SYNONYMS: dict[str, list[str]] = {
    "suv":       ["sport utility", "suv"],
    "truck":     ["pickup", "truck"],
    "sedan":     ["sedan"],
    "van":       ["van"],
    "coupe":     ["coupe"],
    "hatchback": ["hatchback"],
    "convertible": ["convertible"],
    "hybrid":    ["hybrid"],
    "electric":  ["electric", "ev"],
    "diesel":    ["diesel"],
}


def _expand_tokens(tokens: list[str]) -> list[str]:
    """Replace shorthand terms with canonical forms used in the descriptions."""
    expanded = []
    for t in tokens:
        expanded.extend(_SYNONYMS.get(t, [t]))
    return expanded


def search(query: str, budget_text: str | None = None, max_results: int = 3) -> list[dict]:
    """
    Returns up to max_results vehicles matching the query.
    Scores by keyword overlap on description; filters by budget when provided.
    Falls back to book_low for budget comparison on unpriced vehicles.
    """
    raw_tokens = re.sub(r"[^a-z0-9 ]", "", query.lower()).split()
    tokens = _expand_tokens(raw_tokens)
    max_price = _extract_budget(budget_text) if budget_text else None

    scored: list[tuple[int, dict]] = []
    for v in INVENTORY:
        haystack = v["description"].lower()
        score = sum(1 for t in tokens if t in haystack)
        if score == 0:
            continue
        # Budget filter: use actual price if set, else use floor book value as proxy
        effective_price = v["price"] or v["book_low"]
        if max_price and effective_price and effective_price > max_price:
            continue
        scored.append((score, v))

    scored.sort(key=lambda x: (-x[0], x[1]["price"] or x[1]["book_low"] or 999_999))
    return [v for _, v in scored[:max_results]]


def format_vehicle(v: dict) -> str:
    price_str   = f"${v['price']:,}" if v["price"] else "Contact us for pricing"
    mileage_str = f"{v['mileage']:,} mi" if v["mileage"] else "mileage N/A"
    color_str   = f" | {v['color']}" if v["color"] else ""
    return f"{v['description']} — {price_str} | {mileage_str}{color_str} (#{v['stock']})"
