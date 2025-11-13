# config.py
import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
    MINIO_BUCKET = os.getenv("MINIO_BUCKET")

    @staticmethod
    def validate():
        required = ["SQLALCHEMY_DATABASE_URI", "MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY", "MINIO_BUCKET"]
        for var in required:
            if not getattr(Config, var):
                raise ValueError(f"{var} no está definida en .env")