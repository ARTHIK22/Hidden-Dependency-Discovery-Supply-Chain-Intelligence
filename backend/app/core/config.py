from pydantic_settings import BaseSettings


class Settings(BaseSettings):
	APP_NAME: str = "Hidden Dependency Intelligence API"
	DEBUG: bool = True
	DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/dependency_intelligence"
	REDIS_URL: str = "redis://localhost:6379/0"
	API_PREFIX: str = "/api"

	class Config:
		env_file = ".env"


settings = Settings()
