import pytest
from dbtellme.exporters.rag import RAGExporter
from dbtellme.models import (
    SchemaModel, TableModel, ColumnModel, AnnotationModel
)

def _make_schema():
    """Logo ERP-like test schema."""
    trcode_col = ColumnModel(
        name="TRCODE", data_type="SMALLINT",
        annotations=AnnotationModel(
            description="Movement type",
            values={1: "Purchase Invoice", 2: "Sales", 7: "Return"}
        )
    )
    stockref_col = ColumnModel(
        name="STOCKREF", data_type="INT",
        is_foreign_key=True, ref_table="ITEMS", ref_column="LOGICALREF"
    )
    logicalref_col = ColumnModel(
        name="LOGICALREF", data_type="INT",
        is_primary_key=True, is_nullable=False
    )
    stline = TableModel(
        name="STLINE",
        description="Stock movements",
        columns=[logicalref_col, stockref_col, trcode_col],
        sql_examples=[
            "SELECT * FROM STLINE WHERE TRCODE=1",
            "SELECT * FROM STLINE WHERE MONTH(DATE_)=MONTH(GETDATE())"
        ]
    )
    items = TableModel(
        name="ITEMS",
        columns=[
            ColumnModel(name="LOGICALREF", data_type="INT", is_primary_key=True),
            ColumnModel(name="CODE", data_type="VARCHAR(25)"),
        ]
    )
    return SchemaModel(
        tables=[stline, items],
        connection_string_info="mssql database"
    )

def test_chunk_count():
    """STLINE: summary + enum + examples = 3 chunk, ITEMS: summary = 1."""
    schema = _make_schema()
    result = RAGExporter().export(schema)
    assert len(result["chunks"]) == 4  # 3 (STLINE) + 1 (ITEMS)

def test_chunk_ids_unique():
    result = RAGExporter().export(_make_schema())
    ids = [c["id"] for c in result["chunks"]]
    assert len(ids) == len(set(ids))

def test_summary_chunk_structure():
    result = RAGExporter().export(_make_schema())
    summary = next(c for c in result["chunks"] if c["id"] == "table_STLINE")
    assert summary["metadata"]["type"] == "table_summary"
    assert summary["metadata"]["has_enums"] is True
    assert summary["metadata"]["has_fk"] is True
    assert summary["metadata"]["column_count"] == 3
    assert "ITEMS" in summary["metadata"]["related_tables"]
    assert "STOCKREF" in summary["content"]

def test_enum_chunk_contains_values():
    result = RAGExporter().export(_make_schema())
    enum_chunk = next(c for c in result["chunks"] if c["id"] == "table_STLINE_enums")
    assert enum_chunk["metadata"]["type"] == "table_enums"
    assert "Purchase Invoice" in enum_chunk["content"]
    assert "Return" in enum_chunk["content"]
    assert "TRCODE" in enum_chunk["content"]

def test_example_chunk_contains_sql():
    result = RAGExporter().export(_make_schema())
    ex_chunk = next(c for c in result["chunks"] if c["id"] == "table_STLINE_examples")
    assert ex_chunk["metadata"]["type"] == "table_examples"
    assert ex_chunk["metadata"]["example_count"] == 2
    assert "SELECT * FROM STLINE WHERE TRCODE=1" in ex_chunk["content"]

def test_no_enum_chunk_for_items():
    """ITEMS table should not have an enum chunk."""
    result = RAGExporter().export(_make_schema())
    ids = [c["id"] for c in result["chunks"]]
    assert "table_ITEMS_enums" not in ids
