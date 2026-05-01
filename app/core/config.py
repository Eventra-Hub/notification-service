from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    RABBITMQ_URL: str
    PORT: int = 8000
    SERVICE_NAME: str = "notification-service"
    QUEUE_NAME: str = "notification.queue"

    class Config:
        env_file = ".env"

settings = Settings()
