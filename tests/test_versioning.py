import json
import pytest
from dbtellme.models import SchemaModel, TableModel, ColumnModel, AnnotationModel
from dbtellme.exporters.ai_button import AIButtonExporter
from dbtellme.exporters.rag import RAGExporter
from dbtellme.exporters.finetune import FineTuneExporter

def _base_schema():
    col = ColumnModel(name="ID", data_type="INT", is_primary_key=True)
    table = TableModel(name="ORDERS", columns=[col])
    return SchemaModel(tables=[table], connection_string_info="sqlite")

def _annotated_schema():
    col = ColumnModel(
        name="STATUS", data_type="INT",
        annotations=AnnotationModel(values={1: "Active", 0: "Passive"})
    )
    table = TableModel(
        name="ORDERS",
        columns=[col],
        description="Order table",
        sql_examples=["SELECT * FROM ORDERS WHERE STATUS=1"]
    )
    return SchemaModel(tables=[table], connection_string_info="sqlite")

def test_hash_is_deterministic():
    """Same schema should produce same hash every time."""
    s = _base_schema()
    assert s.compute_hash() == s.compute_hash()

def test_hash_changes_on_annotation():
    """Hash should change when annotation is added."""
    before = _base_schema().compute_hash()
    after = _annotated_schema().compute_hash()
    assert before != after

def test_hash_changes_on_enum_update():
    """Hash should change when enum value changes."""
    col1 = ColumnModel(
        name="TRCODE", data_type="INT",
        annotations=AnnotationModel(values={1: "Invoice"})
    )
    col2 = ColumnModel(
        name="TRCODE", data_type="INT",
        annotations=AnnotationModel(values={1: "Purchase Invoice"})  # value changed
    )
    s1 = SchemaModel(tables=[TableModel(name="T", columns=[col1])])
    s2 = SchemaModel(tables=[TableModel(name="T", columns=[col2])])
    assert s1.compute_hash() != s2.compute_hash()

def test_annotation_count():
    s = _annotated_schema()
    count = s.count_annotations()
    # description (1) + sql_examples (1) + enum values (2) = 4
    assert count == 4

def test_ai_button_meta_in_output():
    schema = _annotated_schema()
    output = AIButtonExporter().export(schema, project="test")
    assert "schema_hash" in output
    assert "generated_at" in output

def test_rag_meta_in_output():
    schema = _annotated_schema()
    result = RAGExporter().export(schema, project="test")
    assert "meta" in result
    assert "schema_hash" in result["meta"]
    assert "generated_at" in result["meta"]
    assert "chunks" in result

def test_finetune_meta_first_line():
    schema = _annotated_schema()
    output = FineTuneExporter().export(schema, project="test")
    first_line = json.loads(output.split("\n")[0])
    assert "meta" in first_line
    assert "schema_hash" in first_line["meta"]
    assert "annotation_count" in first_line["meta"]

def test_hash_length():
    """Hash should be 16 characters."""
    assert len(_base_schema().compute_hash()) == 16
