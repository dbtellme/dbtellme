import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class ExportMetaModel(BaseModel):
    """Version metadata attached to every export file."""
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    schema_hash: str = ""
    annotation_count: int = 0
    table_count: int = 0
    project: str = ""
    exporter: str = ""           # "AIButtonExporter" | "RAGExporter" | "FineTuneExporter"
    version: str = "1.0"

class AnnotationModel(BaseModel):
    description: Optional[str] = None
    values: Optional[Dict[Any, str]] = None  # map code value to descriptive text (e.g. 1: "Active")
    ref_table: Optional[str] = None       # Virtual FK target table
    ref_column: Optional[str] = None      # Virtual FK target column

class ColumnModel(BaseModel):
    name: str = Field(..., description="The name of the database column")
    data_type: str = Field(..., description="The type of the data (e.g. INTEGER, VARCHAR, DATE)")
    is_nullable: bool = True
    is_primary_key: bool = False
    is_foreign_key: bool = False
    ref_table: Optional[str] = None
    ref_column: Optional[str] = None
    description: Optional[str] = None
    annotations: Optional[AnnotationModel] = None

class TableModel(BaseModel):
    name: str = Field(..., description="The name of the database table")
    columns: List[ColumnModel] = Field(default_factory=list)
    description: Optional[str] = None
    sql_examples: List[str] = Field(default_factory=list)

class SchemaModel(BaseModel):
    tables: List[TableModel] = Field(default_factory=list)
    connection_string_info: Optional[str] = None

    def get_table(self, table_name: str) -> Optional[TableModel]:
        for table in self.tables:
            if table.name.lower() == table_name.lower():
                return table
        return None

    def compute_hash(self) -> str:
        """
        Generate a deterministic SHA256 hash from schema + annotation content.
        If annotations change, the hash changes → export 'stale' olur.
        """
        fingerprint = []
        for table in sorted(self.tables, key=lambda t: t.name):
            fingerprint.append(f"table:{table.name}")
            fingerprint.append(f"desc:{table.description or ''}")
            for col in sorted(table.columns, key=lambda c: c.name):
                fingerprint.append(f"col:{col.name}:{col.data_type}")
                if col.description:
                    fingerprint.append(f"col_desc:{col.description}")
                if col.annotations:
                    if col.annotations.values:
                        sorted_vals = sorted(col.annotations.values.items())
                        fingerprint.append(f"enum:{json.dumps(sorted_vals)}")
                    if col.annotations.ref_table:
                        fingerprint.append(
                            f"vfk:{col.annotations.ref_table}.{col.annotations.ref_column or 'id'}"
                        )
        raw = "|".join(fingerprint)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]  # 16 karakter yeterli

    def count_annotations(self) -> int:
        """Return the total number of populated annotation fields."""
        count = 0
        for table in self.tables:
            if table.description:
                count += 1
            if table.sql_examples:
                count += len([e for e in table.sql_examples if e.strip()])
            for col in table.columns:
                if col.description:
                    count += 1
                if col.annotations:
                    if col.annotations.values:
                        count += len(col.annotations.values)
                    if col.annotations.ref_table:
                        count += 1
        return count
