from sqlalchemy import create_engine, Engine
from .base import AbstractConnector

class MySQLConnector(AbstractConnector):
    """Connector optimized for MySQL / MariaDB."""

    def create_engine(self) -> Engine:
        return create_engine(
            self.url,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
            connect_args={
                "charset": "utf8mb4",
                "connect_timeout": 10
            }
        )
