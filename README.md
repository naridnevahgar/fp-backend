# fp-backend

Stock market data API built with FastAPI and MongoDB.

## API Endpoints

Base path: `/fp/api/v1`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/fp/api/v1/search?q=&limit=` | Autocomplete search on company name (min 2 chars, limit default 10, max 50) |
| GET | `/fp/api/v1/stocks/{isin}?start_date=&end_date=` | Historical stock data for an ISIN, grouped by exchange |
| GET | `/fp/api/v1/stocks/{isin}/latest` | Most recent trading day data for an ISIN, grouped by exchange |