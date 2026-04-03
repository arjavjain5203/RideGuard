from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://rideguard:rideguard@localhost:5432/rideguard"
    APP_NAME: str = "RideGuard API"
    DEBUG: bool = True

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


settings = Settings()
