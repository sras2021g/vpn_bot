import uuid
from datetime import datetime, timedelta

def generate_key():
    return str(uuid.uuid4())

def get_expiration_date(days=1):
    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
