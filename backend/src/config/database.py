from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os


load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")


# Создаём движок SQLAlchemy
engine = create_engine(DATABASE_URL, echo=True)


# Создаём фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Функция для получения сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
