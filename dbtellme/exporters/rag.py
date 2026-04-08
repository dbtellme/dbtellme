import json
from typing import List, Dict, Any
from .base import AbstractExporter
from ..models import SchemaModel, TableModel, ColumnModel


class RAGExporter(AbstractExporter):
    """
    RAG (Retrieval Augmented Generation) dataset exporter.
    Produces 3 chunk types per table:
      1. table_summary   — general table overview
      2. table_enums     — enum/domain values (if any)
      3. table_examples  — SQL examples and business logic (if any)
    
    Directly compatible with LangChain / LlamaIndex / Pinecone / Chroma.
    """

    def export(self, schema: SchemaModel, project: str = "", **kwargs) -> Dict[str, Any]:
        meta = self.build_meta(schema, project)
        chunks = []
        for table in schema.tables:
            chunks.append(self._summary_chunk(table, schema))
            enum_chunk = self._enum_chunk(table, schema)
            if enum_chunk:
                chunks.append(enum_chunk)
            example_chunk = self._example_chunk(table, schema)
            if example_chunk:
                chunks.append(example_chunk)
        
        return {
            "meta": {
                "schema_hash": meta.schema_hash,
                "generated_at": meta.generated_at,
                "annotation_count": meta.annotation_count,
                "table_count": meta.table_count,
                "project": meta.project,
                "chunk_count": len(chunks),
                "version": meta.version,
            },
            "chunks": chunks
        }

    # ── Chunk 1: Table Summary ─────────────────────────────────────────────────

    def _summary_chunk(self, table: TableModel, schema: SchemaModel) -> Dict:
        # Collect relationships
        physical_fks = []
        virtual_fks = []
        enum_cols = []
        fk_cols = []

        for col in table.columns:
            if col.is_foreign_key and col.ref_table:
                physical_fks.append(f"{col.name} -> {col.ref_table}.{col.ref_column or 'id'}")
                fk_cols.append(col.name)
            if col.annotations and col.annotations.ref_table:
                virtual_fks.append(
                    f"{col.name} ~> {col.annotations.ref_table}.{col.annotations.ref_column or 'id'}"
                )
            if col.annotations and col.annotations.values:
                enum_cols.append(col.name)

        related_tables = list({col.ref_table for col in table.columns 
                                if col.is_foreign_key and col.ref_table})

        # Content text — natural language for embedding quality
        lines = [f"Table: {table.name}"]
        if table.description:
            lines.append(f"Purpose: {table.description}")

        lines.append(f"Database: {schema.connection_string_info or 'Unknown'}")
        lines.append(f"Columns ({len(table.columns)}): " 
                     + ", ".join(f"{c.name} [{c.data_type}]" for c in table.columns))

        if physical_fks:
            lines.append("Physical Foreign Keys: " + " | ".join(physical_fks))
        if virtual_fks:
            lines.append("Virtual Foreign Keys: " + " | ".join(virtual_fks))
        if enum_cols:
            lines.append(f"Enum Columns: {', '.join(enum_cols)} (see enum chunk for values)")
        if table.sql_examples:
            lines.append(f"Has {len(table.sql_examples)} business logic example(s) (see examples chunk)")

        pk_cols = [c.name for c in table.columns if c.is_primary_key]
        if pk_cols:
            lines.append(f"Primary Key: {', '.join(pk_cols)}")

        not_null = [c.name for c in table.columns if not c.is_nullable and not c.is_primary_key]
        if not_null:
            lines.append(f"Required Columns: {', '.join(not_null)}")

        return {
            "id": f"table_{table.name}",
            "metadata": {
                "type": "table_summary",
                "table": table.name,
                "database": schema.connection_string_info,
                "column_count": len(table.columns),
                "has_enums": bool(enum_cols),
                "has_fk": bool(physical_fks),
                "has_virtual_fk": bool(virtual_fks),
                "has_examples": bool(table.sql_examples),
                "enum_columns": enum_cols,
                "fk_columns": fk_cols,
                "related_tables": related_tables,
            },
            "content": "\n".join(lines),
        }

    # ── Chunk 2: Enum / Domain Values ────────────────────────────────────

    def _enum_chunk(self, table: TableModel, schema: SchemaModel) -> Dict | None:
        enum_sections = []

        for col in table.columns:
            if not (col.annotations and col.annotations.values):
                continue
            values_str = "\n".join(
                f"  {code} = {label}" 
                for code, label in col.annotations.values.items()
            )
            section = (
                f"Column: {col.name} ({col.data_type})\n"
                f"Description: {col.description or (col.annotations.description if col.annotations else 'N/A')}\n"
                f"Possible Values:\n{values_str}"
            )
            enum_sections.append(section)

        if not enum_sections:
            return None

        content = (
            f"Enum and Domain Values for Table: {table.name}\n"
            f"{'=' * 50}\n"
            + "\n\n".join(enum_sections)
        )

        enum_col_names = [
            col.name for col in table.columns 
            if col.annotations and col.annotations.values
        ]

        return {
            "id": f"table_{table.name}_enums",
            "metadata": {
                "type": "table_enums",
                "table": table.name,
                "database": schema.connection_string_info,
                "enum_columns": enum_col_names,
                "enum_count": len(enum_sections),
            },
            "content": content,
        }

    # ── Chunk 3: SQL Examples & Business Logic ───────────────────────────────

    def _example_chunk(self, table: TableModel, schema: SchemaModel) -> Dict | None:
        examples = [e.strip() for e in (table.sql_examples or []) if e.strip()]
        if not examples:
            return None

        lines = [
            f"Business Logic and SQL Examples for Table: {table.name}",
            f"{'=' * 50}",
        ]
        for i, ex in enumerate(examples, 1):
            lines.append(f"\nExample {i}:\n{ex}")

        return {
            "id": f"table_{table.name}_examples",
            "metadata": {
                "type": "table_examples",
                "table": table.name,
                "database": schema.connection_string_info,
                "example_count": len(examples),
            },
            "content": "\n".join(lines),
        }
