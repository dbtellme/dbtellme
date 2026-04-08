from abc import ABC, abstractmethod
from typing import Any, Optional
from sqlalchemy import Engine

class AbstractConnector(ABC):
    """Base class for all database connectors."""

    def __init__(self, connection_url: str):
        self._url = connection_url
        self._engine: Optional[Engine] = None

    @property
    def url(self) -> str:
        return self._url

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._engine = self.create_engine()
        return self._engine

    @abstractmethod
    def create_engine(self) -> Engine:
        """Create and return a SQLAlchemy engine."""
        pass

    def test_connection(self) -> bool:
        """Basic check if the connection works."""
        try:
            with self.engine.connect() as conn:
                return True
        except Exception:
            return False
