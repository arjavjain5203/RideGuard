from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://rideguard:rideguard@localhost:5432/rideguard"
    APP_NAME: str = "RideGuard API"
    DEBUG: bool = True
    CORS_ORIGINS: str = "http://localhost:3000"
    SECRET_KEY: str = "rideguard-dev-secret-change-me"
    TOKEN_ISSUER: str = "rideguard-api"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8
    ENABLE_TRIGGER_MONITOR: bool = True

    # Zone multipliers for Bangalore areas
    ZONE_MULTIPLIERS: dict = {
        "koramangala":    1.15,
        "indiranagar":    1.10,
        "hsr_layout":     1.12,
        "whitefield":     1.05,
        "jayanagar":      1.08,
        "btm_layout":     1.10,
        "electronic_city": 1.03,
        "marathahalli":   1.07,
        "default":        1.00,
    }

    class Config:
        env_file = ".env"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
