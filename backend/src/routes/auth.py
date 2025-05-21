from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from src.models import Manager
from src.config.database import get_db
from src.schemas import LoginRequest, SuperuserStatusUpdate
from src.config import logger
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone, date
from typing import Optional
import jwt
import os
from dotenv import load_dotenv


load_dotenv()


router = APIRouter()


# Настройки JWT
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 30


# Настройка хэширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Настройка OAuth2 для получения токена
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


# Функция для создания JWT-токена
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


# Функция для проверки пароля
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# Функция для получения текущего менеджера из токена
async def get_current_manager(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    manager = db.query(Manager).filter(Manager.username == username).first()
    if manager is None:
        raise credentials_exception
    # Проверяем срок действия суперюзера
    if (
        manager.status == "superuser"
        and manager.superuser_expiry
        and manager.superuser_expiry < date.today()
    ):
        manager.status = "regular"
        manager.superuser_expiry = None
        db.commit()
        logger.info(
            f"Истек срок действия статуса суперюзера у пользователя {username}")
    return {"username": manager.username, "status": manager.status}


# Функция для проверки, является ли менеджер суперпользователем
async def get_current_superuser(current_manager: dict = Depends(get_current_manager)):
    if current_manager["status"] != "superuser":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_manager


# Эндпоинт для логина
@router.post("/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    manager = db.query(Manager).filter(
        Manager.username == request.username).first()
    if not manager or not verify_password(request.password, manager.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": manager.username, "status": manager.status},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


# Эндпоинт для изменения статуса менеджера
@router.patch("/{username}/status")
async def grant_superuser_status(
    username: str,
    update_data: SuperuserStatusUpdate,
    db: Session = Depends(get_db),
    current_manager: dict = Depends(get_current_manager)
):
    # Проверяем, является ли текущий менеджер суперпользователем
    current_manager_record = db.query(Manager).filter(
        Manager.username == current_manager["username"]).first()
    if not current_manager_record:
        raise HTTPException(
            status_code=404, detail="Current manager not found")

    is_superuser = current_manager_record.superuser_expiry and current_manager_record.superuser_expiry > date.today()
    if not is_superuser:
        raise HTTPException(
            status_code=403, detail="Only superusers can grant superuser status")

    # Проверяем, существует ли целевой пользователь
    target_manager = db.query(Manager).filter(
        Manager.username == username).first()
    if not target_manager:
        raise HTTPException(status_code=404, detail="Target manager not found")

    # Обновляем статус в зависимости от days
    if update_data.days is None:
        # Если days == null, снимаем статус суперпользователя
        target_manager.superuser_expiry = None
        db.commit()
        logger.info(
            f"Суперпользователь {current_manager['username']} снял статус суперпользователя с {username}")
        return {
            "message": f"Superuser status removed from {username}"
        }
    elif update_data.days < 0:
        # Запрещаем отрицательные значения
        raise HTTPException(
            status_code=400, detail="Кол-во дней должно быть больше или равно 0")
    else:
        # Устанавливаем статус суперпользователя
        expiry_date = date.today() + timedelta(days=update_data.days)
        target_manager.superuser_expiry = expiry_date
        db.commit()
        logger.info(
            f"Суперпользователь {current_manager['username']} наделил статусом суперпользователя {username} до {expiry_date}")
        return {
            "message": f"Superuser status granted to {username} until {expiry_date}"
        }
