
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger


setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s", settings.APP_NAME)
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Systematic Trading Research Platform",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.include_router(router, prefix=settings.API_V1_PREFIX)


@app.get("/")
def root():
    return {
        "message": "QuantTrader API running",
        "version": settings.APP_VERSION,
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "environment": settings.APP_ENV,
    }
