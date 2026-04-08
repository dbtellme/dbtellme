# dbtellme

**Bridge your database to AI pipelines — without touching your schema.**

dbtellme is a local-first dashboard that connects to your database, lets you enrich the schema with business context, and exports it in formats ready for LLMs — RAG pipelines, fine-tuning datasets, and AI prompt schemas.

> Built because manually documenting 30,000 lines of ERP schema annotations is not a workflow.

![dbtellme Dashboard](docs/screenshot.png)

---

## Why dbtellme?

Most "chat with your database" tools focus on generating SQL. dbtellme focuses on something earlier in the chain: **making your database understandable to an LLM in the first place.**

If your database has columns like `TRCODE`, `CARDTYPE`, or `status` that store integer codes — an LLM has no idea what `TRCODE = 7` means. You do. dbtellme gives you a structured way to capture that knowledge once and reuse it everywhere.

|  | dbtellme | Vanna.ai | MindsDB |
|--|----------|----------|---------|
| Target | Schema enrichment → AI export | NL → SQL | AI on structured data |
| Enum / domain mapping | ✅ | ❌ | ❌ |
| RAG-ready chunks | ✅ | ❌ | ❌ |
| Fine-tune dataset | ✅ | ❌ | ❌ |
| Local-first | ✅ | ❌ | ❌ |
| Open source | ✅ | ✅ | ✅ |

---

## Features

- **Schema Explorer** — connect to PostgreSQL, MySQL, MSSQL, or SQLite and instantly see tables, columns, primary keys, and foreign key relationships
- **Annotation Layer** — add table descriptions, column context, enum value mappings, virtual foreign keys, and SQL examples — without modifying your actual database
- **SQL Sandbox** — validate your SQL examples inside the UI using safe rollback transactions
- **Import Docs** — bulk-load descriptions from existing Markdown documentation
- **3 AI Export Formats:**
  - `Export AI Context` — Markdown system prompt for ChatGPT / Claude
  - `Export RAG` — JSON chunks ready for Pinecone, Chroma, LlamaIndex
  - `Export Fine-Tune` — JSONL dataset in ChatML format for LLaMA, Mistral, Unsloth
- **Annotation Templates** — start with pre-built templates for WooCommerce, Magento 2, Odoo, Django, Laravel, and Supabase
- **Export Versioning** — every export includes a `schema_hash` so you always know if your export is stale
- **Connection History** — passwords are automatically scrubbed from saved connection history

---

## Quick Start

### pip

```bash
pip install dbtellme
dbtellme ui
# Open http://localhost:11234
```

### From source

```bash
git clone https://github.com/dbtellme/dbtellme.git
cd dbtellme
pip install -e ".[all-db]"
dbtellme ui
```

### Docker

```bash
# Pull and run
docker run -p 11234:11234 \
  -v ./annotations:/app/annotations \
  dbtellme/dbtellme

# Or with docker-compose
curl -O https://raw.githubusercontent.com/dbtellme/dbtellme/main/docker-compose.yml
docker-compose up
```

Open `http://localhost:11234`

> **Note:** Always mount `./annotations` as a volume — this is where your annotation data lives. Without it, annotations will be lost when the container restarts.

---

## How It Works

```
1. Connect    →  provide a connection string
2. Explore    →  tables, columns, FK relationships auto-detected
3. Annotate   →  add enum mappings, descriptions, SQL examples
4. Export     →  RAG JSON  /  Fine-tune JSONL  /  AI Context MD
```

**Example: Enum mapping**

Your database stores `status = 1`. dbtellme lets you annotate:

```yaml
table: orders
column: status
description: "Order lifecycle status."
values:
  1: "Pending payment"
  2: "Processing"
  3: "Completed"
  4: "Cancelled"
```

This gets embedded into every export — so your LLM knows what `status = 3` means.

---

## Export Formats

### AI Context (`.md`)

Human-readable Markdown for zero-shot LLM queries. Paste into ChatGPT or Claude as a system prompt.

### RAG Dataset (`.json`)

Table-by-table chunks with rich metadata for vector database ingestion (LangChain, LlamaIndex, Pinecone, Chroma):

```json
{
  "meta": { "schema_hash": "a3f9c1d2", "generated_at": "...", "chunk_count": 12 },
  "chunks": [
    {
      "id": "table_orders",
      "metadata": { "type": "table_summary", "has_enums": true, "related_tables": ["customers"] },
      "content": "Table: orders\nPurpose: ..."
    },
    {
      "id": "table_orders_enums",
      "metadata": { "type": "table_enums", "enum_columns": ["status"] },
      "content": "Enum and Domain Values for Table: orders\n..."
    }
  ]
}
```

### Fine-Tune Dataset (`.jsonl`)

ChatML-formatted QA pairs with enum context, FK joins, and your custom SQL examples — ready for Unsloth, LLaMA Factory, Axolotl:

```jsonl
{"messages": [{"role": "system", "content": "Table: orders | status values: 1=Pending, 2=Processing..."}, {"role": "user", "content": "Get processing orders"}, {"role": "assistant", "content": "SELECT * FROM orders WHERE status = 2;"}]}
```

---

## Annotation Templates

Start with a pre-built template instead of annotating from scratch. Select one when creating a new connection — it pre-populates common column descriptions and enum mappings.

| Template | Platform | Database |
|----------|----------|----------|
| `woocommerce` | WooCommerce | MySQL |
| `magento2` | Magento 2 | MySQL |
| `odoo` | Odoo ERP | PostgreSQL |
| `django` | Django Framework | Any |
| `laravel` | Laravel Framework | Any |
| `supabase` | Supabase | PostgreSQL |

**Want to add a template for your platform?** See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## CLI

```bash
# Test a connection
dbtellme connect "sqlite:///mydb.sqlite"

# Scan and save schema as JSON
dbtellme schema "postgresql://user:pass@host/db" --output schema.json

# Export to AI-ready formats
dbtellme export "sqlite:///mydb.sqlite" --format ai-button
dbtellme export "sqlite:///mydb.sqlite" --format rag --output-dir ./exports
dbtellme export "sqlite:///mydb.sqlite" --format finetune --annotations ./annotations
```

---

## Database Support

| Database | Connection string |
|----------|-------------------|
| SQLite | `sqlite:///path/to/db.sqlite` |
| PostgreSQL | `postgresql://user:pass@host:5432/db` |
| MySQL / MariaDB | `mysql+pymysql://user:pass@host:3306/db` |
| SQL Server | `mssql+pyodbc://user:pass@host/db` |

Install the driver for your database:

```bash
pip install "dbtellme[postgres]"   # PostgreSQL
pip install "dbtellme[mysql]"      # MySQL / MariaDB
pip install "dbtellme[mssql]"      # SQL Server
pip install "dbtellme[all-db]"     # All of the above
```

---

## Project Structure

```
dbtellme/
├── connectors/      # DB connection layer (SQLAlchemy)
├── exporters/       # AI Context, RAG, Fine-tune exporters
├── templates/       # Community annotation templates
├── web/             # Flask dashboard
├── enricher.py      # Annotation → schema merger
├── models.py        # Pydantic data models
└── cli.py           # Click CLI
```

---

## Contributing

The best way to contribute is by adding an **annotation template** for a platform you know well. Every template saves other developers hours of manual annotation work.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide. Short version:

1. Create `dbtellme/templates/your_platform/`
2. Add `template.yaml` + annotation YAML files
3. Run `pytest tests/test_templates.py -v`
4. Open a PR

---

## License

MIT — see [LICENSE](LICENSE).

---

*dbtellme — open source, local-first, community-driven.*
