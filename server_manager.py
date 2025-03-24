import httpx
import logging

logger = logging.getLogger(__name__)

async def configure_server(ip, port, username, password, key):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{ip}:{port}/add-user",
                json={"key": key}
            )
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Ошибка при выполнении команды на сервере: {response.text}")
                return False
    except Exception as e:
        logger.error(f"Ошибка при настройке сервера: {e}")
        return False
