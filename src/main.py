from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from loguru import logger

from src.core.config import settings
from src.core import waha_client
from src.core import state as state_manager
from src.database.connection import init_pool, close_pool
from src.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting {} | env={}", settings.dealer_name, settings.app_env)
    await init_pool()
    yield
    logger.info("Shutting down")
    await close_pool()
    await state_manager.close_redis()
    await waha_client.close_client()


app = FastAPI(title="Sky Motors Helper", lifespan=lifespan)
app.include_router(router)
