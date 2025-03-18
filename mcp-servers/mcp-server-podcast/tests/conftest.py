"""
Pytest configuration file.
"""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

from mcp_server_podcast.config import Settings


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    dir_path = Path(tempfile.mkdtemp())
    yield dir_path
    shutil.rmtree(dir_path)


@pytest.fixture
def test_settings(temp_dir):
    """Create test settings with a temporary storage path."""
    test_settings = Settings()
    test_settings.mcp_storage_path = temp_dir / "mcp-storage"
    test_settings.mcp_storage_path.mkdir(parents=True, exist_ok=True)
    return test_settings