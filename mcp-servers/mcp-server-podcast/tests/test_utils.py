"""
Tests for utility functions and classes.
"""

import json
import pytest
from pathlib import Path

from mcp_server_podcast.utils import ResourceIDManager


def test_resource_id_manager_init(temp_dir):
    """Test ResourceIDManager initialization."""
    manager = ResourceIDManager(temp_dir)
    assert manager.storage_path == temp_dir
    assert manager.mappings == {"document": {}, "podcast": {}, "audio": {}, "voice": {}}


def test_resource_id_manager_generate_id(temp_dir):
    """Test ResourceIDManager.generate_id."""
    manager = ResourceIDManager(temp_dir)
    resource_id = manager.generate_id("document")
    assert isinstance(resource_id, str)
    assert len(resource_id) > 0


def test_resource_id_manager_add_mapping(temp_dir):
    """Test ResourceIDManager.add_mapping."""
    manager = ResourceIDManager(temp_dir)
    resource_id = manager.generate_id("document")
    file_path = temp_dir / "test.txt"
    file_path.touch()
    
    metadata = {"name": "test", "type": "text/plain"}
    manager.add_mapping("document", resource_id, file_path, metadata)
    
    # Verify mapping was added
    assert resource_id in manager.mappings["document"]
    assert manager.mappings["document"][resource_id]["file_path"] == str(file_path)
    assert manager.mappings["document"][resource_id]["metadata"] == metadata
    
    # Verify file was created
    assert manager.mappings_file.exists()
    
    # Load the file and verify content
    saved_mappings = json.loads(manager.mappings_file.read_text())
    assert resource_id in saved_mappings["document"]
    assert saved_mappings["document"][resource_id]["file_path"] == str(file_path)
    assert saved_mappings["document"][resource_id]["metadata"] == metadata


def test_resource_id_manager_get_file_path(temp_dir):
    """Test ResourceIDManager.get_file_path."""
    manager = ResourceIDManager(temp_dir)
    resource_id = manager.generate_id("document")
    file_path = temp_dir / "test.txt"
    file_path.touch()
    
    # Add mapping
    manager.add_mapping("document", resource_id, file_path)
    
    # Get file path
    retrieved_path = manager.get_file_path("document", resource_id)
    assert retrieved_path == file_path
    
    # Test non-existent resource
    assert manager.get_file_path("document", "non-existent") is None
    assert manager.get_file_path("non-existent-type", resource_id) is None