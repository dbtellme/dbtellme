#!/usr/bin/env python3
"""
Template validation script — runs in CI on every PR.
Exits with code 1 if any validation rule fails.
"""

import os
import sys
import yaml

TEMPLATES_DIR = os.path.join(
    os.path.dirname(__file__), '..', '..', 'dbtellme', 'templates'
)

REQUIRED_FIELDS = [
    'id', 'name', 'description', 'version',
    'db_types', 'tables_covered', 'author', 'annotation_count'
]

VALID_DB_TYPES = {'mysql', 'mariadb', 'postgresql', 'mssql', 'sqlite'}

errors = []
warnings = []


def err(template_id, msg):
    errors.append(f"  [FAIL] [{template_id}] {msg}")


def warn(template_id, msg):
    warnings.append(f"  [WARN] [{template_id}] {msg}")


def validate_template(folder_path):
    folder_name = os.path.basename(folder_path)

    meta_path = os.path.join(folder_path, 'template.yaml')
    if not os.path.exists(meta_path):
        err(folder_name, "template.yaml not found")
        return

    try:
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = yaml.safe_load(f)
    except yaml.YAMLError as e:
        err(folder_name, f"template.yaml is not valid YAML: {e}")
        return

    template_id = meta.get('id', folder_name)

    for field in REQUIRED_FIELDS:
        if field not in meta or meta[field] is None:
            err(template_id, f"missing required field: '{field}'")

    if meta.get('id') != folder_name:
        err(template_id,
            f"id '{meta.get('id')}' does not match folder name '{folder_name}'")

    db_types = meta.get('db_types', [])
    if not isinstance(db_types, list) or len(db_types) == 0:
        err(template_id, "db_types must be a non-empty list")
    else:
        for dt in db_types:
            if dt not in VALID_DB_TYPES:
                err(template_id,
                    f"invalid db_type '{dt}'. Valid: {sorted(VALID_DB_TYPES)}")

    annotation_files = [
        f for f in os.listdir(folder_path)
        if f.endswith(('.yaml', '.yml')) and f != 'template.yaml'
    ]

    if len(annotation_files) == 0:
        err(template_id, "template has no annotation YAML files")
        return

    declared = meta.get('annotation_count')
    actual = len(annotation_files)
    if declared != actual:
        err(template_id,
            f"annotation_count is {declared} but found {actual} annotation files")

    for filename in annotation_files:
        file_path = os.path.join(folder_path, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                ann = yaml.safe_load(f)
        except yaml.YAMLError as e:
            err(template_id, f"{filename} is not valid YAML: {e}")
            continue

        if not ann:
            err(template_id, f"{filename} is empty")
            continue

        if 'table' not in ann:
            err(template_id, f"{filename} missing 'table' field")
        if 'column' not in ann:
            err(template_id, f"{filename} missing 'column' field")

        if 'values' not in ann and 'ref_table' not in ann and 'description' not in ann:
            warn(template_id,
                 f"{filename} has no 'values', 'ref_table', or 'description'")

        if 'values' in ann and not isinstance(ann['values'], dict):
            err(template_id, f"{filename} 'values' must be a mapping (key: label)")

    print(f"  [OK] {template_id} ({actual} annotation files)")


def main():
    print(f"\nValidating templates in: {os.path.abspath(TEMPLATES_DIR)}\n")

    if not os.path.exists(TEMPLATES_DIR):
        print("[FAIL] templates directory not found")
        sys.exit(1)

    template_dirs = [
        entry.path for entry in os.scandir(TEMPLATES_DIR)
        if entry.is_dir() and not entry.name.startswith('_')
    ]

    if not template_dirs:
        print("[WARN] No template folders found")
        sys.exit(0)

    for folder in sorted(template_dirs):
        validate_template(folder)

    print(f"\nChecked {len(template_dirs)} template(s)")

    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(w)

    if errors:
        print(f"\nErrors ({len(errors)} total):")
        for e in errors:
            print(e)
        print("\n[FAIL] Validation failed. Fix the errors above before merging.\n")
        sys.exit(1)
    else:
        print("\n[OK] All templates are valid.\n")
        sys.exit(0)


if __name__ == '__main__':
    main()
