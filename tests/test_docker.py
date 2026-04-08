import os
import subprocess
import pytest


def docker_available():
    """Check if Docker is installed and running."""
    try:
        # Windows'ta docker.exe, Linux/MAC'te docker
        cmd = 'docker'
        result = subprocess.run(
            [cmd, 'info'],
            capture_output=True, timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


@pytest.mark.skipif(not docker_available(), reason="Docker not available")
def test_dockerfile_builds():
    """Dockerfile should build without errors."""
    result = subprocess.run(
        ['docker', 'build', '-t', 'dbtellme-test', '.'],
        capture_output=True, text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    assert result.returncode == 0, (
        f"Docker build failed:\n{result.stderr}"
    )
    # Temizlik
    subprocess.run(['docker', 'rmi', 'dbtellme-test'], capture_output=True)


def test_dockerignore_exists():
    """`.dockerignore` file should exist."""
    root = os.path.join(os.path.dirname(__file__), '..')
    assert os.path.exists(os.path.join(root, '.dockerignore'))


def test_dockerfile_exists():
    """Dockerfile should exist."""
    root = os.path.join(os.path.dirname(__file__), '..')
    assert os.path.exists(os.path.join(root, 'Dockerfile'))


def test_docker_compose_exists():
    """docker-compose.yml should exist."""
    root = os.path.join(os.path.dirname(__file__), '..')
    assert os.path.exists(os.path.join(root, 'docker-compose.yml'))


def test_cli_ui_has_host_option():
    """CLI ui command should accept --host parameter."""
    result = subprocess.run(
        ['python', '-m', 'dbtellme.cli', 'ui', '--help'],
        capture_output=True, text=True,
        cwd=os.path.join(os.path.dirname(__file__), '..')
    )
    assert '--host' in result.stdout
