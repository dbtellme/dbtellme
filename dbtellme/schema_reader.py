from sqlalchemy import inspect
from typing import List, Optional, Dict
from .models import SchemaModel, TableModel, ColumnModel
from .connectors.base import AbstractConnector

class SchemaReader:
    """Reads database schema from a connector."""

    def __init__(self, connector: AbstractConnector):
        self.connector = connector
        self._inspector = inspect(self.connector.engine)

    def read_schema(self) -> SchemaModel:
        """Analyze the database and return a SchemaModel."""
        tables: List[TableModel] = []
        table_names = self._inspector.get_table_names()

        for table_name in table_names:
            table_model = self._get_table_info(table_name)
            tables.append(table_model)
        
        return SchemaModel(
            tables=tables, 
            connection_string_info=f"{self.connector.engine.name} database"
        )

    def _get_table_info(self, table_name: str) -> TableModel:
        """Analyze a single table and return its model."""
        columns: List[ColumnModel] = []
        
        # Get basic column info
        raw_columns = self._inspector.get_columns(table_name)
        pk_columns = self._inspector.get_pk_constraint(table_name).get('constrained_columns', [])
        
        # Get foreign key info to map them to columns
        fks = self._inspector.get_foreign_keys(table_name)
        fk_map = {}
        for fk in fks:
            for col_name, ref_col in zip(fk['constrained_columns'], fk['referred_columns']):
                fk_map[col_name] = {
                    'ref_table': fk['referred_table'],
                    'ref_column': ref_col
                }

        for col in raw_columns:
            name = col['name']
            col_model = ColumnModel(
                name=name,
                data_type=str(col['type']),
                is_nullable=col.get('nullable', True),
                is_primary_key=(name in pk_columns),
                is_foreign_key=(name in fk_map),
                ref_table=fk_map.get(name, {}).get('ref_table'),
                ref_column=fk_map.get(name, {}).get('ref_column'),
                description=col.get('comment') # SQL comments if available
            )
            columns.append(col_model)

        return TableModel(
            name=table_name,
            columns=columns,
            description=None # Could potentially get from table comments if supported
        )
