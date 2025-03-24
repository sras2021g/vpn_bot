import sqlite3
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_file):
        self.connection = sqlite3.connect(db_file)
        self.cursor = self.connection.cursor()
        self.create_tables()

    def create_tables(self):
        try:
            # Таблица пользователей
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                user_id INTEGER UNIQUE,
                balance REAL DEFAULT 0,
                earned REAL DEFAULT 0,  -- Заработанные средства
                referral_id INTEGER DEFAULT NULL
            )
            """)
            # Таблица ключей
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS keys (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                key TEXT UNIQUE,
                expires_at TEXT,
                server_id INTEGER
            )
            """)
            # Таблица серверов
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY,
                ip TEXT UNIQUE,
                port INTEGER,
                protocol TEXT,
                status TEXT DEFAULT 'active'
            )
            """)
            # Таблица цен
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY,
                tariff TEXT UNIQUE,
                amount REAL
            )
            """)
            # Индексы
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON keys (user_id)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_server_id ON keys (server_id)")
            self.connection.commit()
        except sqlite3.Error as e:
            logger.error(f"Ошибка при создании таблиц: {e}")

    def user_exists(self, user_id):
        try:
            self.cursor.execute("SELECT id FROM users WHERE user_id = ?", (user_id,))
            return self.cursor.fetchone() is not None
        except sqlite3.Error as e:
            logger.error(f"Ошибка в user_exists: {e}")
            return False

    def add_user(self, user_id):
        try:
            with self.connection:
                self.cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        except sqlite3.Error as e:
            logger.error(f"Ошибка при добавлении пользователя: {e}")

    def add_key(self, user_id, key, expires_at, server_id):
        try:
            with self.connection:
                self.cursor.execute("INSERT INTO keys (user_id, key, expires_at, server_id) VALUES (?, ?, ?, ?)", (user_id, key, expires_at, server_id))
        except sqlite3.Error as e:
            logger.error(f"Ошибка при добавлении ключа: {e}")

    def get_user_keys(self, user_id):
        try:
            self.cursor.execute("SELECT key, expires_at FROM keys WHERE user_id = ?", (user_id,))
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Ошибка в get_user_keys: {e}")
            return []

    def key_exists(self, user_id):
        try:
            self.cursor.execute("SELECT id FROM keys WHERE user_id = ?", (user_id,))
            return self.cursor.fetchone() is not None
        except sqlite3.Error as e:
            logger.error(f"Ошибка в key_exists: {e}")
            return False

    def add_server(self, ip, port, protocol):
        try:
            with self.connection:
                self.cursor.execute("INSERT INTO servers (ip, port, protocol) VALUES (?, ?, ?)", (ip, port, protocol))
        except sqlite3.Error as e:
            logger.error(f"Ошибка при добавлении сервера: {e}")

    def get_servers(self):
        try:
            self.cursor.execute("SELECT id, ip, port, protocol FROM servers WHERE status = 'active'")
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Ошибка в get_servers: {e}")
            return []

    def get_server_by_id(self, server_id):
        try:
            self.cursor.execute("SELECT ip, port, protocol FROM servers WHERE id = ?", (server_id,))
            return self.cursor.fetchone()
        except sqlite3.Error as e:
            logger.error(f"Ошибка в get_server_by_id: {e}")
            return None

    def update_server_status(self, server_id, status):
        try:
            with self.connection:
                self.cursor.execute("UPDATE servers SET status = ? WHERE id = ?", (status, server_id))
        except sqlite3.Error as e:
            logger.error(f"Ошибка при обновлении статуса сервера: {e}")

    def get_least_loaded_server(self):
        try:
            servers = self.get_servers()
            if not servers:
                return None

            server_load = {}
            for server in servers:
                server_id = server[0]
                self.cursor.execute("SELECT COUNT(*) FROM keys WHERE server_id = ?", (server_id,))
                load = self.cursor.fetchone()[0]
                server_load[server_id] = load

            least_loaded_server_id = min(server_load, key=server_load.get)
            return least_loaded_server_id
        except sqlite3.Error as e:
            logger.error(f"Ошибка в get_least_loaded_server: {e}")
            return None

    def get_all_keys(self):
        try:
            self.cursor.execute("SELECT user_id, key, expires_at FROM keys")
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Ошибка в get_all_keys: {e}")
            return []

    def get_all_users(self):
        try:
            self.cursor.execute("SELECT user_id FROM users")
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Ошибка в get_all_users: {e}")
            return []

    def block_user(self, user_id):
        try:
            with self.connection:
                self.cursor.execute("DELETE FROM keys WHERE user_id = ?", (user_id,))
        except sqlite3.Error as e:
            logger.error(f"Ошибка при блокировке пользователя: {e}")

    def add_referral(self, user_id, referral_id):
        try:
            with self.connection:
                self.cursor.execute("UPDATE users SET referral_id = ? WHERE user_id = ?", (referral_id, user_id))
        except sqlite3.Error as e:
            logger.error(f"Ошибка при добавлении реферала: {e}")

    def get_referrals(self, user_id):
        try:
            self.cursor.execute("SELECT user_id FROM users WHERE referral_id = ?", (user_id,))
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Ошибка в get_referrals: {e}")
            return []

    def add_earned(self, user_id, amount):
        try:
            with self.connection:
                self.cursor.execute("UPDATE users SET earned = earned + ? WHERE user_id = ?", (amount, user_id))
        except sqlite3.Error as e:
            logger.error(f"Ошибка при добавлении заработка: {e}")

    def get_earned(self, user_id):
        try:
            self.cursor.execute("SELECT earned FROM users WHERE user_id = ?", (user_id,))
            result = self.cursor.fetchone()
            return result[0] if result else 0
        except sqlite3.Error as e:
            logger.error(f"Ошибка в get_earned: {e}")
            return 0

    def add_balance(self, user_id, amount):
        try:
            with self.connection:
                self.cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        except sqlite3.Error as e:
            logger.error(f"Ошибка при пополнении баланса: {e}")

    def get_balance(self, user_id):
        try:
            self.cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            result = self.cursor.fetchone()
            return result[0] if result else 0
        except sqlite3.Error as e:
            logger.error(f"Ошибка в get_balance: {e}")
            return 0

    def get_referral_id(self, user_id):
        try:
            self.cursor.execute("SELECT referral_id FROM users WHERE user_id = ?", (user_id,))
            result = self.cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            logger.error(f"Ошибка в get_referral_id: {e}")
            return None

    def update_price(self, tariff, amount):
        try:
            with self.connection:
                self.cursor.execute("INSERT OR REPLACE INTO prices (tariff, amount) VALUES (?, ?)", (tariff, amount))
        except sqlite3.Error as e:
            logger.error(f"Ошибка при обновлении цены: {e}")

    def get_price(self, tariff):
        try:
            self.cursor.execute("SELECT amount FROM prices WHERE tariff = ?", (tariff,))
            result = self.cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении цены: {e}")
            return None
