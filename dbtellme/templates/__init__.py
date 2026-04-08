import os
import yaml
import shutil
from typing import List, Dict, Optional

TEMPLATES_DIR = os.path.dirname(os.path.abspath(__file__))


class TemplateManager:
    """Manages template discovery, listing, and copying to project directories."""

    def list_templates(self) -> List[Dict]:
        """Read all templates under templates/ and return their metadata."""
        templates = []
        if not os.path.exists(TEMPLATES_DIR):
            return []

        for entry in os.scandir(TEMPLATES_DIR):
            if not entry.is_dir() or entry.name.startswith('_'):
                continue
            meta_path = os.path.join(entry.path, 'template.yaml')
            if not os.path.exists(meta_path):
                continue
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta = yaml.safe_load(f)
                meta['path'] = entry.path
                templates.append(meta)
            except Exception:
                continue
        return sorted(templates, key=lambda t: t.get('name', ''))

    def get_template(self, template_id: str) -> Optional[Dict]:
        """Return metadata for a single template by ID."""
        for t in self.list_templates():
            if t.get('id') == template_id:
                return t
        return None

    def apply_template(self, template_id: str, project_dir: str) -> Dict:
        """
        Copy template YAML files to the target project directory.
        Does not overwrite existing files — only adds missing ones.
        
        Returns:
            {"copied": [...], "skipped": [...], "total": N}
        """
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        os.makedirs(project_dir, exist_ok=True)

        template_path = template['path']
        copied = []
        skipped = []

        for filename in os.listdir(template_path):
            if filename == 'template.yaml':
                continue
            if not (filename.endswith('.yaml') or filename.endswith('.yml')):
                continue

            src = os.path.join(template_path, filename)
            dst = os.path.join(project_dir, filename)

            if os.path.exists(dst):
                skipped.append(filename)
            else:
                shutil.copy2(src, dst)
                copied.append(filename)

        return {
            "template": template.get('name'),
            "copied": copied,
            "skipped": skipped,
            "total": len(copied) + len(skipped),
        }
