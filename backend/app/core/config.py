from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./plant.db"
    seed: int = 20261022

    class Config:
        env_file = ".env"


settings = Settings()
