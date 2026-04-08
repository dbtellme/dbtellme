import click
import os
from rich.console import Console
from rich.table import Table

from .connectors.sqlite import SQLiteConnector
from .connectors.postgres import PostgreSQLConnector
from .connectors.mysql import MySQLConnector
from .connectors.mssql import MSSQLConnector
from .connectors.base import AbstractConnector
from .schema_reader import SchemaReader
from .enricher import SchemaEnricher
from .exporters.ai_button import AIButtonExporter
from .exporters.rag import RAGExporter
from .exporters.finetune import FineTuneExporter

console = Console()


@click.group()
def main():
    """dbtellme — Bridge your database to AI pipelines."""
    pass


@main.command()
@click.argument('url')
def connect(url: str):
    """Test a database connection."""
    connector = _build_connector(url)
    if connector and connector.test_connection():
        console.print(f"[green]Connected successfully:[/green] {url}")
    else:
        console.print(f"[red]Connection failed:[/red] {url}")


@main.command()
@click.argument('url')
@click.option('--output', '-o', default='schema.json', help='Output file path')
def schema(url: str, output: str):
    """Scan a database schema and save it as JSON."""
    connector = _build_connector(url)
    if not connector:
        return

    reader = SchemaReader(connector)
    with console.status("[bold green]Reading schema..."):
        schema_model = reader.read_schema()

    with open(output, 'w', encoding='utf-8') as f:
        f.write(schema_model.model_dump_json(indent=2))

    console.print(f"[green]Schema saved:[/green] {output}")

    table = Table(title="Schema Summary")
    table.add_column("Table", style="cyan")
    table.add_column("Columns", style="magenta")
    for t in schema_model.tables:
        table.add_row(t.name, str(len(t.columns)))
    console.print(table)


@main.command()
@click.argument('url')
@click.option('--format', '-f',
              type=click.Choice(['ai-button', 'rag', 'finetune']),
              default='ai-button', help='Export format')
@click.option('--output-dir', '-d', default='output', help='Output directory')
@click.option('--annotations', '-a', default='annotations',
              help='Annotations directory')
@click.option('--project', '-p', default='', help='Project name')
def export(url: str, format: str, output_dir: str, annotations: str, project: str):
    """Export the enriched schema to AI-ready formats."""
    connector = _build_connector(url)
    if not connector:
        return

    os.makedirs(output_dir, exist_ok=True)
    reader = SchemaReader(connector)
    enricher = SchemaEnricher(annotations)

    with console.status("[bold green]Processing..."):
        schema_model = reader.read_schema()
        schema_model = enricher.enrich(schema_model)

    if format == 'ai-button':
        exporter = AIButtonExporter()
        result = exporter.export(schema_model, project=project)
        output_file = os.path.join(output_dir, "ai_prompt_schema.md")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result)
        console.print(f"[green]Export complete:[/green] {output_file}")

    elif format == 'rag':
        exporter = RAGExporter()
        import json
        result = exporter.export(schema_model, project=project)
        output_file = os.path.join(output_dir, "rag_dataset.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        console.print(f"[green]Export complete:[/green] {output_file}")
        console.print(f"Chunks: {result['meta']['chunk_count']}")

    elif format == 'finetune':
        exporter = FineTuneExporter()
        result = exporter.export(schema_model, project=project)
        output_file = os.path.join(output_dir, "finetune_dataset.jsonl")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result)
        console.print(f"[green]Export complete:[/green] {output_file}")


@main.command()
@click.option('--port', default=11234, help='Port to run the UI on')
@click.option('--host', default='127.0.0.1', help='Host to bind to (use 0.0.0.0 for Docker)')
def ui(port: int, host: str):
    """Launch the web dashboard."""
    try:
        from .web.app import app
        console.print("[bold cyan]dbtellme AI Dashboard[/bold cyan] starting...")
        console.print(f"[green]Open:[/green] http://{host}:{port}")
        app.run(host=host, port=port, debug=False)
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to start UI: {e}")


def _build_connector(url: str) -> AbstractConnector | None:
    """Return the appropriate connector based on the URL scheme."""
    if url.startswith("sqlite"):
        return SQLiteConnector(url)
    elif url.startswith("postgresql") or url.startswith("postgres"):
        return PostgreSQLConnector(url)
    elif url.startswith("mysql"):
        return MySQLConnector(url)
    elif url.startswith("mssql"):
        return MSSQLConnector(url)
    else:
        console.print(
            f"[red]Error:[/red] Unsupported URL scheme. "
            f"Supported: sqlite, postgresql, mysql, mssql"
        )
        return None


if __name__ == "__main__":
    main()
