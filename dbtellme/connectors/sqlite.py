from sqlalchemy import create_engine, Engine
from .base import AbstractConnector

class SQLiteConnector(AbstractConnector):
    """Connector for SQLite databases."""

    def create_engine(self) -> Engine:
        return create_engine(self.url)
