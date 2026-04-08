import json
from typing import List
from .base import AbstractExporter
from ..models import SchemaModel, TableModel


class FineTuneExporter(AbstractExporter):
    """
    Fine-tune dataset exporter.
    Converts enum values, FK relationships, and table descriptions
    into JSONL QA pairs (ChatML format).
    """

    SYSTEM_BASE = (
        "You are a database assistant. "
        "Convert the user's questions into accurate SQL queries "
        "based on the schema information provided below."
    )

    def export(self, schema: SchemaModel, project: str = "", **kwargs) -> str:
        meta = self.build_meta(schema, project)
        
        # First line: meta information (JSONL compatible)
        meta_line = json.dumps({
            "meta": {
                "schema_hash": meta.schema_hash,
                "generated_at": meta.generated_at,
                "annotation_count": meta.annotation_count,
                "table_count": meta.table_count,
                "project": meta.project,
                "version": meta.version,
            }
        }, ensure_ascii=False)

        lines = [meta_line]
        for table in schema.tables:
            sys_prompt = self._build_system_prompt(table)
            lines += self._basic_pairs(table, sys_prompt)
            lines += self._enum_pairs(table, sys_prompt)
            lines += self._fk_pairs(table, sys_prompt)
            lines += self._user_example_pairs(table, sys_prompt)
        return "\n".join(lines)

    def _build_system_prompt(self, table: TableModel) -> str:
        parts = [self.SYSTEM_BASE, f"Table: {table.name}"]
        if table.description:
            parts.append(f"Description: {table.description}")
        for col in table.columns:
            if col.annotations and col.annotations.values:
                enum_str = ", ".join(f"{k}={v}" for k, v in col.annotations.values.items())
                parts.append(f"{col.name} values: {enum_str}")
            if col.is_foreign_key and col.ref_table:
                parts.append(f"{col.name} -> {col.ref_table}.{col.ref_column or 'id'}")
            if col.annotations and col.annotations.ref_table:
                parts.append(f"{col.name} (virtual) -> {col.annotations.ref_table}.{col.annotations.ref_column or 'id'}")
        return " | ".join(parts).replace("\n", " ")

    def _basic_pairs(self, table: TableModel, sys: str) -> List[str]:
        return [
            self._pair(sys, f"List all records from {table.name}", f"SELECT * FROM {table.name};"),
            self._pair(sys, f"How many records are in {table.name}?", f"SELECT COUNT(*) FROM {table.name};"),
        ]

    def _enum_pairs(self, table: TableModel, sys: str) -> List[str]:
        pairs = []
        for col in table.columns:
            if not (col.annotations and col.annotations.values): continue
            for code, label in col.annotations.values.items():
                pairs.append(self._pair(
                    sys, 
                    f"Get {label.lower()} records from {table.name}", 
                    f"SELECT * FROM {table.name} WHERE {col.name} = {code};"
                ))
        return pairs

    def _fk_pairs(self, table: TableModel, sys: str) -> List[str]:
        pairs = []
        for col in table.columns:
            if col.is_foreign_key and col.ref_table:
                ref_col = col.ref_column or "id"
                pairs.append(self._pair(
                    sys,
                    f"Join {table.name} with {col.ref_table}",
                    f"SELECT * FROM {table.name} JOIN {col.ref_table} ON {table.name}.{col.name} = {col.ref_table}.{ref_col};"
                ))
        return pairs

    def _user_example_pairs(self, table: TableModel, sys: str) -> List[str]:
        pairs = []
        for example in (table.sql_examples or []):
            example = example.strip()
            if not example: continue
            upper = example.upper()
            if upper.startswith("SELECT"):
                question = f"Write a business logic query for {table.name}"
            elif upper.startswith("UPDATE"):
                question = f"How do I update records in {table.name}?"
            else:
                question = f"Example query for {table.name}"
            pairs.append(self._pair(sys, question, example))
        return pairs

    def _pair(self, system: str, user: str, assistant: str) -> str:
        return json.dumps({
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
                {"role": "assistant", "content": assistant},
            ]
        }, ensure_ascii=False)
