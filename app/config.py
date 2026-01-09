from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENV: str = "development"
    DATABASE_URL: str
    NEON_API_KEY: str
    NEON_PROJECT_ID: str
    NEON_AUTH_URL: str = "https://auth.neon.tech"
    NEON_AUTH_VERIFY_SSL: bool = True
    
    # Security Configuration
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production-please-use-a-strong-random-key"
    CSRF_SECRET_KEY: str = "csrf-secret-key-change-in-production-please"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Security Configuration (continued)
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_ENABLED: bool = True

    # Stripe Configuration
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_STARTER: str = ""
    STRIPE_PRICE_GROWTH: str = ""
    STRIPE_PRICE_ENTERPRISE: str = ""
    STRIPE_PRICE_IDS: dict = {
        "starter": "",
        "growth": "",
        "enterprise": ""
    }

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
