from sqlalchemy import create_engine, Engine
from .base import AbstractConnector

class PostgreSQLConnector(AbstractConnector):
    """Connector optimized for PostgreSQL."""

    def create_engine(self) -> Engine:
        return create_engine(
            self.url,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
            connect_args={"connect_timeout": 10}
        )
