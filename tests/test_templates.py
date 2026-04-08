import os
import pytest
import tempfile
import yaml
from dbtellme.templates import TemplateManager


def test_list_templates_returns_all():
    templates = TemplateManager().list_templates()
    ids = [t['id'] for t in templates]
    assert 'woocommerce' in ids
    assert 'magento2' in ids
    assert 'odoo' in ids
    assert 'django' in ids
    assert 'laravel' in ids


def test_each_template_has_required_fields():
    for t in TemplateManager().list_templates():
        assert 'id' in t, f"{t} missing id"
        assert 'name' in t
        assert 'description' in t
        assert 'annotation_count' in t
        assert 'db_types' in t


def test_get_template_by_id():
    t = TemplateManager().get_template('odoo')
    assert t is not None
    assert t['id'] == 'odoo'
    assert 'Odoo' in t['name']


def test_get_unknown_template_returns_none():
    assert TemplateManager().get_template('nonexistent') is None


def test_apply_template_copies_yaml_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = TemplateManager().apply_template('woocommerce', tmpdir)
        assert result['total'] > 0
        assert len(result['copied']) > 0
        yaml_files = [f for f in os.listdir(tmpdir) if f.endswith('.yaml')]
        assert len(yaml_files) > 0


def test_apply_template_does_not_overwrite():
    with tempfile.TemporaryDirectory() as tmpdir:
        first = TemplateManager().apply_template('django', tmpdir)
        second = TemplateManager().apply_template('django', tmpdir)
        assert len(second['copied']) == 0
        assert len(second['skipped']) == first['total']


def test_apply_unknown_template_raises():
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(ValueError):
            TemplateManager().apply_template('nonexistent', tmpdir)


def test_woocommerce_order_status_values():
    t = TemplateManager().get_template('woocommerce')
    path = os.path.join(t['path'], 'wp_wc_orders_status.yaml')
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    assert data['table'] == 'wp_wc_orders'
    assert 'wc-pending' in data['values']
    assert 'wc-completed' in data['values']


def test_odoo_sale_order_states():
    t = TemplateManager().get_template('odoo')
    path = os.path.join(t['path'], 'sale_order_state.yaml')
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    assert data['table'] == 'sale_order'
    assert 'draft' in data['values']
    assert 'sale' in data['values']


def test_all_templates_have_yaml_files():
    """Every template should have at least 1 annotation YAML file."""
    for t in TemplateManager().list_templates():
        path = t['path']
        yamls = [f for f in os.listdir(path)
                 if f.endswith('.yaml') and f != 'template.yaml']
        assert len(yamls) > 0, f"{t['id']} has no annotation files"


def test_validate_script_passes_all_templates():
    """CI validation script should pass all existing templates."""
    import subprocess
    script = os.path.join(
        os.path.dirname(__file__), '..', '.github', 'scripts', 'validate_templates.py'
    )
    result = subprocess.run(
        ['python', script],
        capture_output=True, text=True
    )
    assert result.returncode == 0, (
        f"Template validation failed:\n{result.stdout}\n{result.stderr}"
    )
