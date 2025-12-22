from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENV: str = "development"
    DATABASE_URL: str
    NEON_API_KEY: str
    NEON_PROJECT_ID: str
    
    # JWT Configuration
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production-please-use-a-strong-random-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_ENABLED: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
