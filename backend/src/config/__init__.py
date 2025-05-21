from loguru import logger


# Настройка Loguru для записи в файл
logger.add(
    "logs/manager_actions.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    level="INFO",
    rotation="2 month",  # Ротация файла раз в 2 месяца
    retention="3 months",  # Хранить логи 3 месяца
)
