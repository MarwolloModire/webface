from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from src.models import (
    TelegramOrder,
    TelegramOrderItem,
    ManualOrder,
    ManualOrderItem,
    Product,
    Manager,
)
from src.config.database import get_db
from src.config import logger
from src.schemas import OrderUpdate, OrderResponse, OrderCreate
from src.routes.auth import get_current_manager
from datetime import date
from sqlalchemy import func
from typing import List


router = APIRouter()


# Объединение заказов из telegram и app
@router.get("/", response_model=List[OrderResponse])
async def get_orders(
    db: Session = Depends(get_db), current_manager: dict = Depends(get_current_manager)
):
    telegram_orders = db.query(TelegramOrder).all()
    manual_orders = db.query(ManualOrder).all()

    orders = []
    for order in telegram_orders:
        items = (
            db.query(TelegramOrderItem)
            .filter(TelegramOrderItem.order_id == order.id)
            .all()
        )
        content = [{"product_name": item.product_name, "quantity": item.quantity}
                   for item in items] if items else []
        orders.append(
            {
                "id": order.id,
                "created_at": order.payment_date,
                "organization": order.contractor_name,
                "invoice_number": order.account_number,
                "manager": order.manager_name,
                "status": order.order_status,
                "closed_at": str(order.closed_at) if order.closed_at else None,
                "source": "telegram",
                "content": content,
            }
        )

    for order in manual_orders:
        items = (
            db.query(ManualOrderItem).filter(
                ManualOrderItem.order_id == order.id).all()
        )
        content = (
            [
                {"product_name": item.product_name, "quantity": item.quantity}
                for item in items
            ]
            if items
            else None
        )
        orders.append(
            {
                "id": order.id,
                "created_at": str(order.created_at),
                "organization": order.organization,
                "invoice_number": order.invoice_number,
                "manager": order.manager,
                "status": order.status,
                "closed_at": str(order.closed_at) if order.closed_at else None,
                "source": order.source,
                "content": content,
            }
        )

    return orders


# Обновление заказа
@router.patch("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: int,
    update_data: OrderUpdate,
    db: Session = Depends(get_db),
    current_manager: dict = Depends(get_current_manager),
):
    # Определяем источник заказа
    telegram_order = (
        db.query(TelegramOrder).filter(TelegramOrder.id == order_id).first()
    )
    manual_order = db.query(ManualOrder).filter(
        ManualOrder.id == order_id).first()

    if not telegram_order and not manual_order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    order = telegram_order if telegram_order else manual_order
    item_model = TelegramOrderItem if telegram_order else ManualOrderItem

    # Проверяем права доступа
    manager = current_manager["username"]
    order_manager = getattr(
        order, "manager_name" if telegram_order else "manager")
    manager_record = db.query(Manager).filter(
        Manager.username == manager).first()
    is_superuser = (
        manager_record
        and manager_record.superuser_expiry
        and manager_record.superuser_expiry > date.today()
    )
    if manager != order_manager and not is_superuser:
        raise HTTPException(
            status_code=403, detail="У Вас нет прав на изменение этого заказа"
        )
    logger.info(f"Мэнагер {manager} начал изменение заказа {order_id}")

    # Обновляем статус и closed_at
    if update_data.order_status:
        # Определяем допустимые статусы в зависимости от модели
        valid_statuses = (
            [s.value for s in order.__table__.columns["status"].type.enums]
            if telegram_order
            else ["Заказ оплачен", "Заказ в работе", "Заказ в пути", "Заказ закрыт"]
        )

        if update_data.order_status not in valid_statuses:
            raise HTTPException(status_code=400, detail="Invalid order status")

        # Устанавливаем статус в зависимости от модели
        old_status = getattr(
            order, "order_status" if telegram_order else "status")
        setattr(
            order,
            "order_status" if telegram_order else "status",
            update_data.order_status,
        )

        if update_data.order_status == "Заказ закрыт" and not getattr(
            order, "closed_at" if telegram_order else "closed_at"
        ):
            setattr(
                order, "closed_at" if telegram_order else "closed_at", date.today())

        logger.info(
            f"Мэнагер {manager} изменяет заказ {order_id} со статуса {old_status} на статус {update_data.order_status}"
        )

    # Обновляем содержимое (продукты)
    if update_data.content:
        logger.info(f"Мэнагер {manager} изменяет содержимое заказа {order_id}")

        # Удаляем старые записи
        db.query(item_model).filter(item_model.order_id == order_id).delete()
        # Проверяем и добавляем новые продукты
        for item in update_data.content:
            product = (
                db.query(Product)
                .filter(func.lower(Product.name) == func.lower(item.product_name))
                .first()
            )
            if not product:
                raise HTTPException(
                    status_code=404,
                    detail=f"Товар с названием '{item.product_name}' не найден",
                )
            if item.quantity <= 0:
                raise HTTPException(
                    status_code=400, detail="Количество должно быть положительным"
                )
            new_item = item_model(
                order_id=order_id,
                product_name=item.product_name,
                quantity=item.quantity,
            )
            db.add(new_item)

    db.commit()
    db.refresh(order)

    # Получаем обновлённые данные
    items = db.query(item_model).filter(item_model.order_id == order_id).all()
    content = (
        [
            {"product_name": item.product_name, "quantity": item.quantity}
            for item in items
        ]
        if items
        else None
    )

    # Возвращаем ответ в формате OrderResponse
    return OrderResponse(
        id=order.id,
        created_at=str(order.payment_date)
        if isinstance(order, TelegramOrder)
        else str(order.created_at),
        organization=order.contractor_name
        if isinstance(order, TelegramOrder)
        else order.organization,
        invoice_number=order.account_number
        if isinstance(order, TelegramOrder)
        else order.invoice_number,
        manager=order.manager_name
        if isinstance(order, TelegramOrder)
        else order.manager,
        status=getattr(order, "order_status" if telegram_order else "status"),
        closed_at=str(
            getattr(order, "closed_at" if telegram_order else "closed_at"))
        if getattr(order, "closed_at" if telegram_order else "closed_at")
        else None,
        source="telegram" if isinstance(order, TelegramOrder) else "manual",
        content=content,
    )


# Создание нового заказа
@router.post("/", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate = Body(...),
    db: Session = Depends(get_db),
    current_manager: dict = Depends(get_current_manager),
):
    # Проверка наличия продуктов и валидация количества
    if order_data.content:
        for item in order_data.content:
            product = (
                db.query(Product)
                .filter(func.lower(Product.name) == func.lower(item.product_name))
                .first()
            )
            if not product:
                raise HTTPException(
                    status_code=400, detail=f"Product '{item.product_name}' not found"
                )
            if item.quantity <= 0:
                raise HTTPException(
                    status_code=400, detail="Quantity must be positive")

    # Создание заказа
    new_order = ManualOrder(
        created_at=date.today(),
        organization=order_data.organization,
        invoice_number=order_data.invoice_number,
        manager=order_data.manager,
        status="Заказ оплачен",
        source="manual",
    )
    db.add(new_order)
    db.flush()

    # Логирование
    acting_manager = current_manager["username"]
    logger.info(f"Мэнагер {acting_manager} создал новый заказ {new_order.id}")

    # Добавление содержимого, если есть
    if order_data.content:
        logger.info(
            f"Мэнагер {acting_manager} добавил содержимое к заказу {new_order.id}"
        )
        for item in order_data.content:
            new_item = ManualOrderItem(
                order_id=new_order.id,
                product_name=item.product_name,
                quantity=item.quantity,
            )
            db.add(new_item)

    db.commit()
    db.refresh(new_order)

    # Получаем элементы заказа
    items = (
        db.query(ManualOrderItem).filter(
            ManualOrderItem.order_id == new_order.id).all()
    )
    content = (
        [
            {"product_name": item.product_name, "quantity": item.quantity}
            for item in items
        ]
        if items
        else None
    )

    # Возвращаем ответ в формате OrderResponse
    return OrderResponse(
        id=new_order.id,
        created_at=str(new_order.created_at),
        organization=new_order.organization,
        invoice_number=new_order.invoice_number,
        manager=new_order.manager,
        status=new_order.status,
        closed_at=str(new_order.closed_at) if new_order.closed_at else None,
        source=new_order.source,
        content=content,
    )


# Удаление заказа
@router.delete("/{order_id}", status_code=204)
async def delete_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_manager: dict = Depends(get_current_manager),
):
    # Определяем источник заказа
    telegram_order = (
        db.query(TelegramOrder).filter(TelegramOrder.id == order_id).first()
    )
    manual_order = db.query(ManualOrder).filter(
        ManualOrder.id == order_id).first()

    if not telegram_order and not manual_order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    order = telegram_order if telegram_order else manual_order
    item_model = TelegramOrderItem if telegram_order else ManualOrderItem

    # Проверяем права доступа
    manager = current_manager["username"]
    order_manager = getattr(
        order, "manager_name" if telegram_order else "manager")
    manager_record = db.query(Manager).filter(
        Manager.username == manager).first()
    is_superuser = (
        manager_record
        and manager_record.superuser_expiry
        and manager_record.superuser_expiry > date.today()
    )
    if manager != order_manager and not is_superuser:
        raise HTTPException(
            status_code=403, detail="У Вас нет прав на изменение этого заказа"
        )
    logger.info(f"Мэнагер {manager} начал удаление заказа {order_id}")

    # Удаляем связанные элементы
    db.query(item_model).filter(item_model.order_id == order_id).delete()

    # Удаляем сам заказ
    db.delete(order)
    db.commit()

    logger.info(f"Мэнагер {manager} успешно удалил заказ {order_id}")

    return
