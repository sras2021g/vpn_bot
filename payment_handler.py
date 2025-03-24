import httpx

async def create_payment(amount, description):
    # Возвращаем заглушку вместо реальной оплаты
    return {
        "id": "test_payment_id",
        "confirmation": {
            "confirmation_url": "https://example.com/payment"  # Заглушка
        }
    }

async def check_payment_status(payment_id):
    # Возвращаем успешный статус для тестирования
    return {"status": "succeeded"}
