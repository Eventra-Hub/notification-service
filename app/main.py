from fastapi import FastAPI
from app.core.rabbitmq import connect_rabbitmq, close_rabbitmq
from app.core.redis import connect_redis, close_redis

app = FastAPI(title="notification-service")

@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "notification-service"}

@app.on_event("startup")
async def startup():
    await connect_redis()
    await connect_rabbitmq()

@app.on_event("shutdown")
async def shutdown():
    await close_rabbitmq()
    await close_redis()
