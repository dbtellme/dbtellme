import json
from dbtellme.exporters.finetune import FineTuneExporter
from dbtellme.models import SchemaModel, TableModel, ColumnModel, AnnotationModel

def test_basic_pairs_generated():
    table = TableModel(name="ORDERS", columns=[])
    schema = SchemaModel(tables=[table])
    output = FineTuneExporter().export(schema)
    # Skipping the first line (meta JSON)
    lines = [json.loads(l) for l in output.strip().split("\n")[1:]]
    assert len(lines) >= 2

def test_enum_pairs_generated():
    col = ColumnModel(
        name="TRCODE", data_type="SMALLINT",
        annotations=AnnotationModel(values={1: "Purchase Invoice", 2: "Sales"})
    )
    table = TableModel(name="STLINE", columns=[col])
    schema = SchemaModel(tables=[table])
    output = FineTuneExporter().export(schema)
    assert "WHERE TRCODE = 1" in output
    assert "WHERE TRCODE = 2" in output

def test_fk_join_generated():
    col = ColumnModel(
        name="CLIENTREF", data_type="INT",
        is_foreign_key=True, ref_table="CLCARD", ref_column="LOGICALREF"
    )
    table = TableModel(name="INVOICE", columns=[col])
    schema = SchemaModel(tables=[table])
    output = FineTuneExporter().export(schema)
    assert "JOIN CLCARD" in output

def test_system_prompt_contains_enum():
    col = ColumnModel(
        name="STATUS", data_type="INT",
        annotations=AnnotationModel(values={0: "Passive", 1: "Active"})
    )
    table = TableModel(name="ITEMS", columns=[col])
    schema = SchemaModel(tables=[table])
    output = FineTuneExporter().export(schema)
    # The first result pair is on the second line (index 1)
    second_line = json.loads(output.split("\n")[1])
    system_content = second_line["messages"][0]["content"]
    assert "STATUS" in system_content
    assert "Active" in system_content
