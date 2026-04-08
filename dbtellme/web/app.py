import os
import yaml
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from dbtellme.schema_reader import SchemaReader
from dbtellme.enricher import SchemaEnricher
from dbtellme.exporters.ai_button import AIButtonExporter
from dbtellme.templates import TemplateManager
from dbtellme.connectors.base import AbstractConnector
from dbtellme.connectors.sqlite import SQLiteConnector

app = Flask(__name__)

# Resolve paths
ANNOTATIONS_DIR = os.path.join(os.getcwd(), 'annotations')
HISTORY_DB = os.path.join(os.getcwd(), 'dbtellme_history.db')

# ═══ Connection History Database ═══
def init_history_db():
    conn = sqlite3.connect(HISTORY_DB)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            mode TEXT NOT NULL,
            connection_url TEXT,
            path TEXT,
            db_type TEXT,
            host TEXT,
            port TEXT,
            username TEXT,
            db_name TEXT,
            table_count INTEGER DEFAULT 0,
            last_connected TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_history_db()

def save_connection_history(data, url_info, table_count):
    conn = sqlite3.connect(HISTORY_DB)
    mode = data.get('mode')
    now = datetime.now().isoformat()
    
    # Securing custom URI so they don't leak passwords to local SQLite history (Gap #1)
    safe_uri = data.get('uri', '')
    if mode == 'uri' and safe_uri:
        import urllib.parse
        try:
            parsed = urllib.parse.urlparse(safe_uri)
            if parsed.password:
                safe_netloc = parsed.netloc.replace(f":{parsed.password}@", ":***@")
                safe_uri = parsed._replace(netloc=safe_netloc).geturl()
        except:
            pass

    # Use the project name or fallback to auto-generated
    name = data.get('project_name', '').strip()
    if not name:
        if mode == 'sqlite': name = os.path.basename(data.get('path', 'unknown'))
        elif mode == 'uri': name = safe_uri[:50]
        else: name = f"{data.get('type','db')}://{data.get('host','')}:{data.get('port','')}/{data.get('name','')}"

    path = data.get('path', '') if mode == 'sqlite' else ''

    # Check if this connection already exists (by mode + identifying info)
    if mode == 'sqlite':
        existing = conn.execute('SELECT id FROM connections WHERE mode=? AND path=?', (mode, path)).fetchone()
    elif mode == 'uri':
        existing = conn.execute('SELECT id FROM connections WHERE mode=? AND connection_url=?', (mode, safe_uri)).fetchone()
    else:
        existing = conn.execute('SELECT id FROM connections WHERE mode=? AND host=? AND port=? AND db_name=? AND db_type=?',
            (mode, data.get('host',''), data.get('port',''), data.get('name',''), data.get('type',''))).fetchone()
    
    if existing:
        conn.execute('UPDATE connections SET last_connected=?, table_count=?, name=? WHERE id=?',
            (now, table_count, name, existing[0]))
    else:
        conn.execute('''
            INSERT INTO connections (name, mode, connection_url, path, db_type, host, port, username, db_name, table_count, last_connected)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            name, mode, safe_uri, path, 
            data.get('type', ''), data.get('host', ''), data.get('port', ''), 
            data.get('user', ''), data.get('name', ''), table_count, now
        ))
    conn.commit()
    conn.close()

def create_sample_db():
    db_path = os.path.join(os.getcwd(), 'sample.db')
    if not os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, category_id INTEGER, price REAL)")
        cursor.execute("CREATE TABLE categories (id INTEGER PRIMARY KEY, name TEXT)")
        cursor.execute("INSERT INTO categories (name) VALUES ('Electronics'), ('Home')")
        cursor.execute("INSERT INTO products (name, category_id, price) VALUES ('Laptop', 1, 1200), ('Chair', 2, 150)")
        conn.commit()
        conn.close()
    return f"sqlite:///{db_path}"

@app.route('/')
def index():
    return render_template('index.html')

# ═══ Connection History API ═══
@app.route('/api/connections', methods=['GET'])
def get_connections():
    conn = sqlite3.connect(HISTORY_DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute('SELECT * FROM connections ORDER BY last_connected DESC LIMIT 20').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/connections/<int:conn_id>', methods=['DELETE'])
def delete_connection(conn_id):
    conn = sqlite3.connect(HISTORY_DB)
    conn.execute('DELETE FROM connections WHERE id=?', (conn_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/browse-file', methods=['GET'])
def browse_file():
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    file_path = filedialog.askopenfilename(
        title="Select SQLite Database",
        filetypes=[
            ("SQLite Database", "*.db *.sqlite *.sqlite3 *.s3db"),
            ("All Files", "*.*")
        ]
    )
    root.destroy()
    return jsonify({"path": file_path})

def _get_generic_connector(url: str) -> AbstractConnector:
    from sqlalchemy import create_engine, Engine
    class GenericConnector(AbstractConnector):
        def create_engine(self) -> Engine:
            return create_engine(self.url)
    return GenericConnector(url)

from dbtellme.connectors.postgres import PostgreSQLConnector
from dbtellme.connectors.mysql import MySQLConnector
from dbtellme.connectors.mssql import MSSQLConnector

def _build_connector(data: dict) -> AbstractConnector:
    """
    Build a connector from request data dict.
    mode: 'sqlite' | 'uri' | 'remote'
    """
    mode = data.get('mode')
    if mode == 'sqlite':
        path = data.get('path')
        url = create_sample_db() if path == 'sample.db' else f"sqlite:///{path}"
        return SQLiteConnector(url)
    elif mode == 'uri':
        url = data.get('uri', '')
        if url.startswith('postgresql'): return PostgreSQLConnector(url)
        if url.startswith('mysql'): return MySQLConnector(url)
        if url.startswith('mssql'): return MSSQLConnector(url)
        return _get_generic_connector(url)
    elif mode == 'remote':
        db_type = data.get('type', 'postgresql')
        prefix_map = {
            'postgresql': 'postgresql://',
            'mysql':      'mysql+pymysql://',
            'mssql':      'mssql+pyodbc://',
        }
        prefix = prefix_map.get(db_type, 'postgresql://')
        url = f"{prefix}{data.get('user')}:{data.get('pass')}@{data.get('host')}:{data.get('port')}/{data.get('name')}"
        connector_map = {
            'postgresql': PostgreSQLConnector,
            'mysql':      MySQLConnector,
            'mssql':      MSSQLConnector,
        }
        cls = connector_map.get(db_type, PostgreSQLConnector)
        return cls(url)
    
    raise ValueError(f"Unknown connection mode: {mode}")
@app.route('/api/connect', methods=['POST'])
def connect():
    data = request.json
    mode = data.get('mode')
    project_name = data.get('project_name', '').strip()
    
    if not project_name:
        return jsonify({"error": "Project name is required"}), 400

    proj_dir = os.path.join(ANNOTATIONS_DIR, "".join(x for x in project_name if x.isalnum() or x in "._- "))

    try:
        connector = _build_connector(data)

        reader = SchemaReader(connector)
        schema = reader.read_schema()
        schema = SchemaEnricher(proj_dir).enrich(schema)
        
        # Load table-level and column-level metadata from project-specific annotation YAML files
        from dbtellme.models import AnnotationModel
        for table in schema.tables:
            table_yaml = os.path.join(proj_dir, f"{table.name.lower()}_meta.yaml")
            if os.path.exists(table_yaml):
                with open(table_yaml, 'r', encoding='utf-8') as f:
                    meta = yaml.safe_load(f) or {}
                    table.description = meta.get('description', table.description)
                    sqls = meta.get('sql_examples', [])
                    table.sql_examples = [sqls] if isinstance(sqls, str) else sqls
            
            for col in table.columns:
                col_yaml = os.path.join(proj_dir, f"{table.name.lower()}_{col.name.lower()}.yaml")
                if os.path.exists(col_yaml):
                    with open(col_yaml, 'r', encoding='utf-8') as f:
                        ann = yaml.safe_load(f) or {}
                        if not col.annotations:
                            col.annotations = AnnotationModel()
                        
                        if ann.get('ref_table'): 
                            col.annotations.ref_table = ann['ref_table']
                            col.annotations.ref_column = ann.get('ref_column', 'id')
                        if ann.get('values'):
                            col.annotations.values = ann['values']
                        if ann.get('description'):
                            col.annotations.description = ann['description']

        url_info = f"{connector.engine.name}://{connector.engine.url.host or 'local'}"
        
        # Save to connection history
        save_connection_history(data, url_info, len(schema.tables))
        
        return jsonify({"schema": schema.model_dump(), "url_info": url_info, "project_name": project_name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/test-sql', methods=['POST'])
def test_sql():
    try:
        data = request.json
        connector = _build_connector(data)
            
        from sqlalchemy import text
        query = data.get('query', '').strip()
        if not query: return jsonify({"error": "Empty query provided."}), 400

        with connector.engine.connect() as conn:
            trans = conn.begin()
            try:
                res = conn.execute(text(query))
                if res.returns_rows:
                    rows = [dict(row._mapping) for row in res.fetchmany(5)]
                else:
                    rows = [{"status": f"{res.rowcount} rows affected (rolled back automatically)."}]
                trans.rollback()
                return jsonify({"result": rows})
            except Exception as e:
                trans.rollback()
                return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/import-annotations', methods=['POST'])
def import_annotations():
    try:
        data = request.json
        project_name = data.get('project_name')
        content = data.get('content', '')
        if not project_name: return jsonify({"error": "Project name required."}), 400
        
        proj_dir = os.path.join(ANNOTATIONS_DIR, project_name)
        os.makedirs(proj_dir, exist_ok=True)
        
        lines = content.split('\n')
        current_table = None
        current_column = None
        
        # Very simple Markdown Parser:
        # # Table: NAME -> Start Table Meta
        # ## Column: NAME -> Start Column Meta
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # Logic: Parse "# Table: users" or "## Column: id"
            if line.lower().startswith('# table:'):
                current_table = line.split(':', 1)[1].strip().lower()
                current_column = None
            elif line.lower().startswith('## column:'):
                current_column = line.split(':', 1)[1].strip().lower()
            elif current_table:
                # Append to description if it's text under the header
                filename = f"{current_table}_meta.yaml" if not current_column else f"{current_table}_{current_column}.yaml"
                filepath = os.path.join(proj_dir, filename)
                
                existing = {}
                if os.path.exists(filepath):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        existing = yaml.safe_load(f) or {}
                
                # Append line to description
                old_desc = existing.get('description', '')
                new_desc = (old_desc + "\n" + line).strip() if old_desc else line
                existing['description'] = new_desc
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(existing, f)
                    
        return jsonify({"success": True, "message": "Annotations imported and merged."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/save-table-annotation', methods=['POST'])
def save_table_annotation():
    data = request.json
    table, description = data.get('table'), data.get('description')
    sql_examples = data.get('sql_examples')
    project_name = data.get('project_name', '').strip()
    proj_dir = os.path.join(ANNOTATIONS_DIR, "".join(x for x in project_name if x.isalnum() or x in "._- "))
    
    os.makedirs(proj_dir, exist_ok=True)
    filepath = os.path.join(proj_dir, f"{table.lower()}_meta.yaml")
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump({"table": table, "description": description, "sql_examples": sql_examples}, f, allow_unicode=True)
    return jsonify({"success": True})

@app.route('/api/save-annotation', methods=['POST'])
def save_annotation():
    data = request.json
    table, column = data.get('table'), data.get('column')
    description = data.get('description')
    values = data.get('values', {})
    ref_table = data.get('ref_table')
    ref_column = data.get('ref_column')
    project_name = data.get('project_name', '').strip()
    
    proj_dir = os.path.join(ANNOTATIONS_DIR, "".join(x for x in project_name if x.isalnum() or x in "._- "))
    os.makedirs(proj_dir, exist_ok=True)
    filepath = os.path.join(proj_dir, f"{table.lower()}_{column.lower()}.yaml")
    
    annotation_data = {
        "table": table,
        "column": column,
        "description": description,
        "values": values
    }
    if ref_table:
        annotation_data["ref_table"] = ref_table
        annotation_data["ref_column"] = ref_column or 'id'
    
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(annotation_data, f, allow_unicode=True)
    return jsonify({"success": True})

def _safe_name(name):
    return "".join(x for x in name if x.isalnum() or x in "._- ")

@app.route('/api/export', methods=['POST'])
def export_schema():
    try:
        data = request.json
        project_name = data.get('project_name', '').strip()
        if not project_name: return jsonify({"error": "Project name is required"}), 400

        proj_dir = os.path.join(ANNOTATIONS_DIR, _safe_name(project_name))
        connector = _build_connector(data)

        reader = SchemaReader(connector)
        schema = SchemaEnricher(proj_dir).enrich(reader.read_schema())
        
        for table in schema.tables:
            table_yaml = os.path.join(proj_dir, f"{table.name.lower()}_meta.yaml")
            if os.path.exists(table_yaml):
                with open(table_yaml, 'r', encoding='utf-8') as f:
                    meta = yaml.safe_load(f)
                    table.description = meta.get('description', table.description)
                    saved_sqls = meta.get('sql_examples', [])
                    if isinstance(saved_sqls, str): table.sql_examples = [saved_sqls] if saved_sqls.strip() else []
                    else: table.sql_examples = saved_sqls

        exporter = AIButtonExporter()
        md_text = exporter.export(schema, project=project_name)
        schema_hash = schema.compute_hash()
        
        return jsonify({
            "markdown": md_text, 
            "filename": f"ai_prompt_{project_name.replace(' ', '_')}.md",
            "schema_hash": schema_hash,
            "generated_at": exporter.build_meta(schema).generated_at,
            "annotation_count": schema.count_annotations(),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def _get_export_schema(request):
    data = request.json
    project_name = data.get('project_name', '').strip()
    proj_dir = os.path.join(ANNOTATIONS_DIR, "".join(x for x in project_name if x.isalnum() or x in "._- "))

    connector = _build_connector(data)

    reader = SchemaReader(connector)
    schema = SchemaEnricher(proj_dir).enrich(reader.read_schema())
    for table in schema.tables:
        table_yaml = os.path.join(proj_dir, f"{table.name.lower()}_meta.yaml")
        if os.path.exists(table_yaml):
            with open(table_yaml, 'r', encoding='utf-8') as f:
                meta = yaml.safe_load(f)
                table.description = meta.get('description', table.description)
                saved_sqls = meta.get('sql_examples', [])
                if isinstance(saved_sqls, str): table.sql_examples = [saved_sqls] if saved_sqls.strip() else []
                else: table.sql_examples = saved_sqls
    return schema

@app.route('/api/export-rag', methods=['POST'])
def export_rag():
    try:
        from dbtellme.exporters.rag import RAGExporter
        schema = _get_export_schema(request)
        project_name = request.json.get('project_name', 'db')
        exporter = RAGExporter()
        result = exporter.export(schema, project=project_name)
        return jsonify({
            "json": result["chunks"],
            "meta": result["meta"],
            "filename": f"rag_{project_name.replace(' ', '_')}.json",
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/export-finetune', methods=['POST'])
def export_finetune():
    try:
        from dbtellme.exporters.finetune import FineTuneExporter
        schema = _get_export_schema(request)
        project_name = request.json.get('project_name', 'db')
        exporter = FineTuneExporter()
        content = exporter.export(schema, project=project_name)
        schema_hash = schema.compute_hash()
        return jsonify({
            "content": content,
            "filename": f"finetune_{project_name.replace(' ', '_')}.jsonl",
            "schema_hash": schema_hash,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/schema-hash', methods=['POST'])
def get_schema_hash():
    """
    Return the current schema + annotation hash.
    The UI compares this value against the stored export hash to show a stale warning.
    """
    try:
        schema = _get_export_schema(request)
        return jsonify({
            "schema_hash": schema.compute_hash(),
            "annotation_count": schema.count_annotations(),
            "table_count": len(schema.tables),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/templates', methods=['GET'])
def list_templates():
    """List all available templates."""
    try:
        manager = TemplateManager()
        templates = manager.list_templates()
        # Remove path field — not exposed to client
        for t in templates:
            t.pop('path', None)
        return jsonify({"templates": templates})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/apply-template', methods=['POST'])
def apply_template():
    """
    Apply the selected template to the project directory.
    Can be called before or after connecting.
    """
    try:
        data = request.json
        template_id = data.get('template_id')
        project_name = data.get('project_name', '').strip()

        if not template_id:
            return jsonify({"error": "template_id required"}), 400
        if not project_name:
            return jsonify({"error": "project_name required"}), 400

        proj_dir = os.path.join(ANNOTATIONS_DIR, _safe_name(project_name))

        manager = TemplateManager()
        result = manager.apply_template(template_id, proj_dir)

        return jsonify({
            "success": True,
            "message": f"{result['template']} template applied.",
            "copied": result['copied'],
            "skipped": result['skipped'],
            "total": result['total'],
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=11234)
