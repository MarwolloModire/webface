from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routes import auth, orders, products

app = FastAPI(
    title="Plasto Orders API",
    description="API for managing orders in Plasto application",
    version="1.0.0",
)

# Подключаем маршруты
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(orders.router, prefix="/api/orders", tags=["orders"])
app.include_router(products.router, prefix="/api/products", tags=["products"])


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Welcome to Plasto Orders API"}
