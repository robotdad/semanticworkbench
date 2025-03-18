import os
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings

log_level = os.environ.get("LOG_LEVEL", "INFO")

def load_required_env_var(env_var_name: str) -> str:
    value = os.environ.get(env_var_name, "")
    if not value:
        raise ValueError(f"Missing required environment variable: {env_var_name}")
    return value


class Settings(BaseSettings):
    """Configuration settings for the Podcast MCP Server."""
    # Logging and server settings
    log_level: str = log_level
    mcp_storage_path: Path = Path(os.environ.get("MCP_STORAGE_PATH", "/tmp/mcp-server-podcast"))
    
    # Azure OpenAI settings
    azure_openai_endpoint: Optional[str] = os.environ.get("AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: Optional[str] = os.environ.get("AZURE_OPENAI_API_KEY")
    azure_openai_api_version: str = os.environ.get("AZURE_OPENAI_API_VERSION", "2023-05-15")
    azure_openai_deployment: str = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
    
    # Azure Document Intelligence settings
    document_intelligence_endpoint: Optional[str] = os.environ.get("DOCUMENT_INTELLIGENCE_ENDPOINT")
    document_intelligence_api_key: Optional[str] = os.environ.get("DOCUMENT_INTELLIGENCE_API_KEY")
    document_intelligence_model_id: str = os.environ.get("DOCUMENT_INTELLIGENCE_MODEL_ID", "prebuilt-layout")
    
    # Azure Speech settings
    speech_resource_id: Optional[str] = os.environ.get("SPEECH_RESOURCE_ID")
    speech_region: Optional[str] = os.environ.get("SPEECH_REGION")
    speech_key: Optional[str] = os.environ.get("SPEECH_KEY")
    speech_host_voice: str = os.environ.get("SPEECH_HOST_VOICE", "en-US-JennyNeural")
    speech_reporter_voices: List[str] = os.environ.get("SPEECH_REPORTER_VOICES", "en-US-GuyNeural,en-US-DavisNeural").split(",")
    
    # Authentication settings
    use_managed_identity: bool = os.environ.get("USE_MANAGED_IDENTITY", "False").lower() == "true"
    
    # Podcast generation settings
    default_podcast_length_minutes: int = int(os.environ.get("DEFAULT_PODCAST_LENGTH_MINUTES", "5"))
    show_transitions: bool = os.environ.get("SHOW_TRANSITIONS", "True").lower() == "true"
    
    def __init__(self):
        super().__init__()
        # Ensure storage path exists
        self.mcp_storage_path.mkdir(parents=True, exist_ok=True)
    
