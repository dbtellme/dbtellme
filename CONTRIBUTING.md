# Contributing to dbtellme

Thank you for considering a contribution! The most impactful way to contribute
is by adding **annotation templates** for platforms you know well.
Every template saves other developers hours of manual annotation work.

---

## Table of Contents

- [Adding a Template](#adding-a-template)
- [Template Format Reference](#template-format-reference)
- [Annotation File Format](#annotation-file-format)
- [Validation Rules](#validation-rules)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Other Contributions](#other-contributions)

---

## Adding a Template

A template is a folder inside `dbtellme/templates/` containing:
- One `template.yaml` — metadata about the platform
- One or more annotation YAML files — column descriptions and enum mappings

### Step-by-step

**1. Fork and clone the repository**
```bash
git clone https://github.com/dbtellme/dbtellme.git
cd dbtellme
pip install -e ".[dev]"
```

**2. Create your template folder**

Use lowercase and underscores only:
```bash
mkdir dbtellme/templates/your_platform
```

Good: `shopify`, `prestashop`, `keycloak`, `supabase`
Bad: `MyPlatform`, `my-platform`, `my platform`

**3. Create `template.yaml`**
```yaml
id: your_platform
name: "Your Platform Name"
description: "One sentence about what this platform is and what the template covers."
version: "1.0"
db_types:
  - mysql           # options: mysql, mariadb, postgresql, mssql, sqlite
tables_covered:
  - orders
  - products
author: "Your Name or GitHub handle"
annotation_count: 2   # must equal the number of annotation YAML files
```

**4. Create annotation YAML files**

Naming: `tablename_columnname.yaml`

```yaml
table: orders
column: status
description: "Lifecycle status of an order."
values:
  pending: "Awaiting payment"
  processing: "Payment confirmed, being fulfilled"
  completed: "Fully delivered"
  cancelled: "Cancelled"
```

**5. Run tests**
```bash
pytest tests/test_templates.py -v
```

**6. Open a Pull Request**

Title: `feat(templates): add <platform> template`

---

## Template Format Reference

| Field | Required | Description |
|-------|----------|-------------|
| `id` | ✅ | Unique ID, must match folder name |
| `name` | ✅ | Human-readable name shown in UI |
| `description` | ✅ | One sentence description |
| `version` | ✅ | Start with `"1.0"` |
| `db_types` | ✅ | Database engines (mysql/mariadb/postgresql/mssql/sqlite) |
| `tables_covered` | ✅ | List of table names |
| `author` | ✅ | Your name or GitHub handle |
| `annotation_count` | ✅ | Must equal actual annotation file count |

---

## Annotation File Format

**Column with enum values:**
```yaml
table: orders
column: status
description: "Order lifecycle status."
values:
  pending: "Awaiting payment"
  completed: "Fully delivered"
```

**Column with virtual foreign key:**
```yaml
table: order_items
column: product_id
description: "References the product for this line item."
ref_table: products
ref_column: id
```

**Tips:**
- English only — templates must be universally readable
- Be specific in descriptions — "Order status" is weak
- Cover all known enum values
- Skip obvious columns (`id`, `created_at`, `updated_at`)

---

## Validation Rules

CI automatically checks:

| Rule | Details |
|------|---------|
| `template.yaml` exists | Required in every template folder |
| Required fields present | All 8 fields must be present |
| `id` matches folder name | `id: shopify` must be in `templates/shopify/` |
| `db_types` are valid | Only allowed values |
| `annotation_count` is accurate | Must match actual file count |
| At least 1 annotation file | Template cannot be empty |
| YAML syntax valid | All files must parse cleanly |
| `table` and `column` present | Every annotation file must have both |

---

## Other Contributions

- **Bug fixes** — open an issue first for non-trivial changes
- **Connector improvements** — better pool settings, new DB support
- **Exporter enhancements** — better RAG chunking, new output formats

For anything beyond templates, open an issue before writing code.

---

## Questions?

Open a [GitHub Discussion](https://github.com/dbtellme/dbtellme/discussions).
Issues are for bugs and confirmed feature requests only.
