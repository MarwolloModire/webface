from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.models import Product
from src.config.database import get_db
from sqlalchemy import func

router = APIRouter()


# Эндпоинт для получения списка всех продуктов
@router.get("/")
async def get_products(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    return [{"id": p.id, "name": p.name} for p in products]


# Эндпоинт для поиска продуктов по частичному совпадению (без учёта регистра)
@router.get("/search")
async def search_products(query: str, db: Session = Depends(get_db)):
    products = (
        db.query(Product)
        .filter(func.lower(Product.name).like(f"%{query.lower()}%"))
        .all()
    )
    if not products:
        raise HTTPException(status_code=404, detail="No products found")
    return [{"id": p.id, "name": p.name} for p in products]
