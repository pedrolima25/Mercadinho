import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./supermercado.db")
    secret_key: str = os.getenv("SECRET_KEY", "chave-secreta-padrao-troque-em-producao")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))
    app_name: str = os.getenv("APP_NAME", "SuperMarket Pro")
    market_name: str = os.getenv("MARKET_NAME", os.getenv("APP_NAME", "Mercadinho"))
    market_logo_url: str = os.getenv("MARKET_LOGO_URL", "/static/img/logo.svg")
    pix_key: str = os.getenv("PIX_KEY", "")
    pix_city: str = os.getenv("PIX_CITY", "MANAUS")
    cosmos_api_token: str = os.getenv("COSMOS_API_TOKEN", "")

settings = Settings()
