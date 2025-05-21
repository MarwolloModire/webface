from sqlalchemy import Column, Integer, String, Date, ForeignKey, Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import ENUM
import enum


Base = declarative_base()


# Определяем ENUM для order_status
class OrderStatus(enum.Enum):
    PAID = "Заказ оплачен"
    WORKING = "Заказ в работе"
    IN_TRANSIT = "Заказ в пути"
    CLOSED = "Заказ закрыт"

    @classmethod
    def get_values(cls):
        return [e.value for e in cls]


# Модель для telegram.orders
class TelegramOrder(Base):
    __tablename__ = "orders"
    __table_args__ = {"schema": "telegram"}

    id = Column(Integer, primary_key=True, index=True)
    payment_date = Column(String(20), nullable=False)
    payment_number = Column(String(20), nullable=False)
    payment_amount = Column(Numeric(15, 2), nullable=False)
    account_number = Column(String(20), nullable=False)
    contractor_name = Column(String(255), nullable=False)
    manager_name = Column(String(70), nullable=True)
    order_status = Column(
        ENUM(*OrderStatus.get_values(), name="orderstatus"),
        nullable=False,
        default="Заказ оплачен",
    )
    highlight_color = Column(String(10), nullable=False, default="red")
    closed_at = Column(Date, nullable=True)


# Модель для telegram.order_items
class TelegramOrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = {"schema": "telegram"}

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("telegram.orders.id"), nullable=False)
    product_name = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False)


# Модель для app.manual_orders
class ManualOrder(Base):
    __tablename__ = "manual_orders"
    __table_args__ = {"schema": "app"}

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(Date, nullable=False)
    organization = Column(String(255), nullable=False)
    invoice_number = Column(String(20), nullable=False)
    manager = Column(String(70), nullable=False)
    status = Column(ENUM(*OrderStatus.get_values(), name="orderstatus"), nullable=False)
    closed_at = Column(Date, nullable=True)
    source = Column(String(20), nullable=False, default="manual")


# Модель для app.order_items
class ManualOrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = {"schema": "app"}

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("app.manual_orders.id"), nullable=False)
    product_name = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False)


# Модель для app.products
class Product(Base):
    __tablename__ = "products"
    __table_args__ = {"schema": "app"}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)


# Модель для auth.managers
class Manager(Base):
    __tablename__ = "managers"
    __table_args__ = {"schema": "auth"}

    username = Column(String(70), primary_key=True, index=True)
    password_hash = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="regular")
    superuser_expiry = Column(Date, nullable=True)
