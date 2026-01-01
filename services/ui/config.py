import os
from dotenv import load_dotenv

load_dotenv()

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "real_estate")
POSTGRES_USER = os.getenv("POSTGRES_USER", "mlops")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "mlops123")
