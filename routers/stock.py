import re
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from db import get_db
from models import (
    ExchangeData,
    LatestStockResponse,
    SearchItem,
    SearchResponse,
    StockDataResponse,
    StockEntry,
)

router = APIRouter()

_ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}\d$")


def _map_entry(entry: dict) -> dict:
    dt = entry["dt"]
    if isinstance(dt, datetime):
        dt = dt.strftime("%Y-%m-%d")
    return {
        "date": dt,
        "symbol": entry["sym"],
        "open": entry["o"],
        "high": entry["h"],
        "low": entry["l"],
        "close": entry["c"],
        "last": entry["la"],
        "prev_close": entry["pc"],
        "total_traded_qty": entry["tq"],
        "total_traded_val": entry["tv"],
        "total_trades": entry["tt"],
    }


# ── Search ──────────────────────────────────────────────────────────────────


@router.get("/search", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
):
    db = get_db()
    regex = {"$regex": f".*{re.escape(q)}.*", "$options": "i"}
    cursor = (
        db["isin"]
        .find(
            {"COMPANY_NAME": regex},
            {"_id": 1, "COMPANY_NAME": 1, "NSE_SYMBOL": 1, "BSE_CODE": 1},
        )
        .limit(limit)
    )
    results = [
        SearchItem(
            isin=doc["_id"],
            name=doc["COMPANY_NAME"],
            nse_symbol=doc.get("NSE_SYMBOL"),
            bse_code=doc.get("BSE_CODE"),
        )
        for doc in cursor
    ]
    return SearchResponse(results=results, count=len(results))


# ── Historical data ─────────────────────────────────────────────────────────


@router.get("/stocks/{isin}", response_model=StockDataResponse)
def get_stock_data(
    isin: str,
    start_date: str | None = None,
    end_date: str | None = None,
):
    if not _ISIN_RE.match(isin):
        raise HTTPException(400, "Invalid ISIN format")

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
        end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
    except ValueError:
        raise HTTPException(400, "Invalid date format, use YYYY-MM-DD")

    start_month = start.strftime("%Y-%m") if start else "0000-00"
    end_month = end.strftime("%Y-%m") if end else "9999-99"

    pipeline: list[dict] = [
        {"$match": {"_id": {"$gte": f"{isin}_{start_month}", "$lte": f"{isin}_{end_month}"}}},
        {"$unwind": "$d"},
    ]

    dt_filter: dict = {}
    if start:
        dt_filter["d.dt"] = {"$gte": start}
    if end:
        dt_filter.setdefault("d.dt", {})["$lte"] = end
    if dt_filter:
        pipeline.append({"$match": dt_filter})

    pipeline.append({"$sort": {"d.dt": 1}})
    pipeline.append({"$replaceRoot": {"newRoot": "$d"}})

    db = get_db()
    results = list(db["raw_bhav_data_v3"].aggregate(pipeline))

    if not results:
        raise HTTPException(404, f"No data found for ISIN {isin}")

    nse_data = [_map_entry(doc) for doc in results if doc["ex"] == "nse"]
    bse_data = [_map_entry(doc) for doc in results if doc["ex"] == "bse"]

    return StockDataResponse(
        isin=isin,
        nse=ExchangeData(count=len(nse_data), data=nse_data) if nse_data else None,
        bse=ExchangeData(count=len(bse_data), data=bse_data) if bse_data else None,
    )


# ── Latest ──────────────────────────────────────────────────────────────────


@router.get("/stocks/{isin}/latest", response_model=LatestStockResponse)
def get_latest_stock(
    isin: str,
):
    if not _ISIN_RE.match(isin):
        raise HTTPException(400, "Invalid ISIN format")

    db = get_db()
    doc = db["raw_bhav_data_v3"].find_one(
        {"_id": {"$gte": f"{isin}_", "$lte": f"{isin}_~"}},
        sort=[("_id", -1)],
    )

    if not doc or not doc.get("d"):
        raise HTTPException(404, f"No data found for ISIN {isin}")

    entries = doc["d"]
    entries.sort(key=lambda e: e["dt"], reverse=True)

    nse_entry = next((e for e in entries if e["ex"] == "nse"), None)
    bse_entry = next((e for e in entries if e["ex"] == "bse"), None)

    if not nse_entry and not bse_entry:
        raise HTTPException(404, f"No data found for ISIN {isin}")

    return LatestStockResponse(
        isin=isin,
        nse=StockEntry(**_map_entry(nse_entry)) if nse_entry else None,
        bse=StockEntry(**_map_entry(bse_entry)) if bse_entry else None,
    )
