from contextlib import asynccontextmanager

from fastapi import FastAPI

from db import close, connect
from routers.stock import router as stock_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    connect()
    yield
    close()


app = FastAPI(lifespan=lifespan)
app.include_router(stock_router, prefix="/fp/api/v1")