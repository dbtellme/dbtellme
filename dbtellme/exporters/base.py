from abc import ABC, abstractmethod
from ..models import SchemaModel, ExportMetaModel

class AbstractExporter(ABC):
    """Base class for all schema exporters."""

    @abstractmethod
    def export(self, schema: SchemaModel, **kwargs):
        """Export the schema to a file or format."""
        pass

    def build_meta(self, schema: SchemaModel, project: str = "") -> ExportMetaModel:
        """Shared meta builder called by all exporters."""
        return ExportMetaModel(
            schema_hash=schema.compute_hash(),
            annotation_count=schema.count_annotations(),
            table_count=len(schema.tables),
            project=project,
            exporter=self.__class__.__name__,
        )
