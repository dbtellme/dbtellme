from sqlalchemy import create_engine, Engine
from .base import AbstractConnector

class MSSQLConnector(AbstractConnector):
    """Connector optimized for SQL Server."""

    def create_engine(self) -> Engine:
        return create_engine(
            self.url,
            fast_executemany=True,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30
        )
