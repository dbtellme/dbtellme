import yaml
import os
from typing import List
from .models import SchemaModel, AnnotationModel

class SchemaEnricher:
    """Enriches the base schema with domain-specific annotations from YAML files."""

    def __init__(self, annotation_dir: str):
        self.annotation_dir = annotation_dir

    def enrich(self, schema: SchemaModel) -> SchemaModel:
        """Apply all annotations in the directory to the schema."""
        if not os.path.exists(self.annotation_dir):
            return schema

        for filename in os.listdir(self.annotation_dir):
            if filename.endswith(".yaml") or filename.endswith(".yml"):
                filepath = os.path.join(self.annotation_dir, filename)
                self._apply_annotation_file(filepath, schema)
        
        return schema

    def _apply_annotation_file(self, filepath: str, schema: SchemaModel):
        """Reads a single YAML file and applies it to the schema."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            table_name = data.get('table')
            column_name = data.get('column')
            
            if not table_name or not column_name:
                return

            table = schema.get_table(table_name)
            if not table:
                return

            column = next((c for c in table.columns if c.name.lower() == column_name.lower()), None)
            if not column:
                return

            # Apply annotations
            column.description = data.get('description', column.description)
            
            if 'values' in data or 'ref_table' in data:
                column.annotations = AnnotationModel(
                    description=data.get('description'),
                    values=data.get('values'),
                    ref_table=data.get('ref_table'),
                    ref_column=data.get('ref_column')
                )
        except Exception:
            # For now, silently skip malformed files as per "yut" (swallow) rule (meaningful error could be logged)
            pass
