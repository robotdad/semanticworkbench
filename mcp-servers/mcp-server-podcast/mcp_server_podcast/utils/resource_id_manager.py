"""
Resource ID manager for handling MCP resources.
"""

import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List


class ResourceIDManager:
    """Manages resource IDs and mappings between IDs and file paths."""
    
    def __init__(self, storage_path: Path):
        """Initialize the resource ID manager.
        
        Args:
            storage_path: Base path for storage
        """
        self.storage_path = storage_path
        self.mappings_file = storage_path / "resource_mappings.json"
        self.mappings = self._load_mappings()
        
    def _load_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Load resource mappings from storage."""
        if not self.mappings_file.exists():
            return {"document": {}, "podcast": {}, "audio": {}, "voice": {}}
            
        try:
            return json.loads(self.mappings_file.read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            return {"document": {}, "podcast": {}, "audio": {}, "voice": {}}
        
    def _save_mappings(self) -> None:
        """Save resource mappings to storage."""
        self.mappings_file.parent.mkdir(parents=True, exist_ok=True)
        self.mappings_file.write_text(json.dumps(self.mappings, indent=2))
        
    def generate_id(self, resource_type: str) -> str:
        """Generate a unique ID for a resource type.
        
        Args:
            resource_type: Type of resource (document, podcast, audio, voice)
            
        Returns:
            Unique ID for the resource
        """
        return str(uuid.uuid4())
        
    def add_mapping(self, resource_type: str, resource_id: str, file_path: Path, metadata: Dict[str, Any] = None) -> None:
        """Add a mapping for a resource ID.
        
        Args:
            resource_type: Type of resource (document, podcast, audio, voice)
            resource_id: Unique ID for the resource
            file_path: Path to the resource file
            metadata: Optional metadata for the resource
        """
        if resource_type not in self.mappings:
            self.mappings[resource_type] = {}
            
        self.mappings[resource_type][resource_id] = {
            "file_path": str(file_path),
            "metadata": metadata or {}
        }
        
        self._save_mappings()
        
    def get_file_path(self, resource_type: str, resource_id: str) -> Optional[Path]:
        """Get file path for a resource ID.
        
        Args:
            resource_type: Type of resource (document, podcast, audio, voice)
            resource_id: Unique ID for the resource
            
        Returns:
            Path to the resource file, or None if not found
        """
        if resource_type not in self.mappings or resource_id not in self.mappings[resource_type]:
            return None
            
        path_str = self.mappings[resource_type][resource_id]["file_path"]
        return Path(path_str)
        
    def get_metadata(self, resource_type: str, resource_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a resource ID.
        
        Args:
            resource_type: Type of resource (document, podcast, audio, voice)
            resource_id: Unique ID for the resource
            
        Returns:
            Metadata for the resource, or None if not found
        """
        if resource_type not in self.mappings or resource_id not in self.mappings[resource_type]:
            return None
            
        return self.mappings[resource_type][resource_id].get("metadata", {})
        
    def update_metadata(self, resource_type: str, resource_id: str, metadata: Dict[str, Any]) -> bool:
        """Update metadata for a resource ID.
        
        Args:
            resource_type: Type of resource (document, podcast, audio, voice)
            resource_id: Unique ID for the resource
            metadata: New metadata (will be merged with existing)
            
        Returns:
            True if successful, False otherwise
        """
        if resource_type not in self.mappings or resource_id not in self.mappings[resource_type]:
            return False
            
        current = self.mappings[resource_type][resource_id].get("metadata", {})
        current.update(metadata)
        self.mappings[resource_type][resource_id]["metadata"] = current
        
        self._save_mappings()
        return True
        
    def list_resources(self, resource_type: str) -> List[str]:
        """List all resources of a given type.
        
        Args:
            resource_type: Type of resource (document, podcast, audio, voice)
            
        Returns:
            List of resource IDs
        """
        if resource_type not in self.mappings:
            return []
            
        return list(self.mappings[resource_type].keys())
        
    def delete_resource(self, resource_type: str, resource_id: str) -> bool:
        """Delete a resource mapping.
        
        Args:
            resource_type: Type of resource (document, podcast, audio, voice)
            resource_id: Unique ID for the resource
            
        Returns:
            True if successful, False otherwise
        """
        if resource_type not in self.mappings or resource_id not in self.mappings[resource_type]:
            return False
            
        del self.mappings[resource_type][resource_id]
        self._save_mappings()
        return True