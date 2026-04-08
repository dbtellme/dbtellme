import pytest
from dbtellme.connectors.sqlite import SQLiteConnector
from dbtellme.connectors.postgres import PostgreSQLConnector
from dbtellme.connectors.mysql import MySQLConnector
from dbtellme.connectors.mssql import MSSQLConnector

def test_sqlite_connector_creates():
    c = SQLiteConnector("sqlite:///sample.db")
    # Note: test_connection actually tries to open it. We don't have sample.db always.
    assert c.url == "sqlite:///sample.db"

def test_build_connector_sqlite():
    from dbtellme.web.app import _build_connector
    c = _build_connector({"mode": "sqlite", "path": "sample.db"})
    assert isinstance(c, SQLiteConnector)

def test_build_connector_uri_postgres():
    from dbtellme.web.app import _build_connector
    c = _build_connector({"mode": "uri", "uri": "postgresql://user:pass@host/db"})
    assert isinstance(c, PostgreSQLConnector)

def test_build_connector_uri_mysql():
    from dbtellme.web.app import _build_connector
    c = _build_connector({"mode": "uri", "uri": "mysql+pymysql://user:pass@host/db"})
    assert isinstance(c, MySQLConnector)
