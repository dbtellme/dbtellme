import json
import os
from .base import AbstractExporter
from ..models import SchemaModel

class AIButtonExporter(AbstractExporter):
    """Exporter for 'AI Button' system prompt schema (Markdown for LLMs)."""

    def export(self, schema: SchemaModel, project: str = "", **kwargs) -> str:
        """Generates a Markdown representation of the schema for AI system prompts."""
        meta = self.build_meta(schema, project)
        
        # Generate Markdown content
        md_content = [
            f"# Enhanced Database Schema Context",
            f"<!-- schema_hash: {meta.schema_hash} | generated_at: {meta.generated_at} | annotations: {meta.annotation_count} -->",
            f"**Database Type:** `{schema.connection_string_info}`\n",
            f"This document defines the schema, table relationships, metadata, enum mappings, and business rules for the database engine. Use this when writing code or SQL queries.\n",
            f"---\n"
        ]

        for table in schema.tables:
            md_content.append(f"## Table: `{table.name}`")
            if table.description:
                md_content.append(f"**Table Purpose:** {table.description}")
            if table.sql_examples:
                md_content.append("**Usage Rules & Examples:**")
                for ex in table.sql_examples:
                    md_content.append(f"```sql\n{ex}\n```")
                md_content.append("")
            
            md_content.append("### Columns")
            for col in table.columns:
                flags = []
                if col.is_primary_key: flags.append("PK")
                if col.is_foreign_key and col.ref_table:
                    flags.append(f"FK -> {col.ref_table}.{col.ref_column or 'id'}")
                if col.annotations and col.annotations.ref_table:
                    flags.append(f"Virtual FK -> {col.annotations.ref_table}.{col.annotations.ref_column or 'id'}")
                if not col.is_nullable: flags.append("NOT NULL")

                flags_str = f" [{', '.join(flags)}]" if flags else ""
                md_content.append(f"- `{col.name}` ({col.data_type}){flags_str}")
                
                if col.description:
                    md_content.append(f"  - *Description:* {col.description}")
                
                if col.annotations and col.annotations.values:
                    enums_str = ", ".join([f"'{k}': '{v}'" for k, v in col.annotations.values.items()])
                    md_content.append(f"  - *Enum Mapping:* {enums_str}")
            
            md_content.append("\n---")
            
        return "\n".join(md_content)
