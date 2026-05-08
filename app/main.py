from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging
from app.core.config import settings
from app.core.redis import connect_redis, close_redis, client
from app.core.rabbitmq import connect_rabbitmq, close_rabbitmq,connection as rmq_conn
from app.routes.notifications import router

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)
@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_redis()         
    logger.info("Redis connected")
    await connect_rabbitmq()     
    yield
    await close_rabbitmq()
    await close_redis()

app = FastAPI(
    title=settings.SERVICE_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router, prefix="/notifications", tags=["notifications"])

@app.get("/health")
async def health():
    from app.core.redis import client
    from app.core.rabbitmq import connection

    status = {
        "service":  settings.SERVICE_NAME,
        "redis":    "unknown",
        "rabbitmq": "unknown",
    }
    try:
        await client.ping()         
        status["redis"] = "connected"
    except Exception as e:
        # Logging the error here helps you see WHY it's unreachable in the terminal
        logging.error(f"Health check Redis error: {e}")
        status["redis"] = "unreachable"

    # 3. Test RabbitMQ
    status["rabbitmq"] = (
        "connected" if connection and not connection.is_closed
        else "unreachable"
    )

    # 4. Determine Overall Status
    overall = "ok" if "unreachable" not in status.values() else "degraded"
    status["status"] = overall

    if overall == "degraded":
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content=status)

    return status