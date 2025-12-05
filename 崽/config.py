# config.py
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = "dev-secret-key-change-me"  # 可以改长一点
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "novel_site.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
