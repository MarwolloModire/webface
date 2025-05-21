from pydantic import BaseModel
from typing import List, Optional


# Модель для запроса логина
class LoginRequest(BaseModel):
    username: str
    password: str


# Модель для элемента содержимого (продукта)
class OrderItem(BaseModel):
    product_name: str
    quantity: int


# Модель для создания заказа
class OrderCreate(BaseModel):
    organization: str
    invoice_number: str
    manager: str
    content: List[OrderItem]


# Модель для обновления заказа
class OrderUpdate(BaseModel):
    order_status: Optional[str] = None
    closed_at: Optional[str] = None
    content: Optional[List[OrderItem]] = None


# Модель ответа для заказа
class OrderResponse(BaseModel):
    id: int
    created_at: str
    organization: str
    invoice_number: str
    manager: Optional[str] = None
    status: str
    closed_at: Optional[str] = None
    source: str
    content: Optional[List[OrderItem]] = None


# Схема для запроса наделения статусом суперпользователя
class SuperuserStatusUpdate(BaseModel):
    days: Optional[int] = None
