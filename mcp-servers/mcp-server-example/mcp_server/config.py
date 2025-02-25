import os
import logging
from typing import Optional
from pydantic_settings import BaseSettings

log_level = os.environ.get("LOG_LEVEL", "INFO")

logger = logging.getLogger("mcp_server_example")

def load_required_env_var(env_var_name: str) -> str:
    value = os.environ.get(env_var_name, "")
    if not value:
        raise ValueError(f"Missing required environment variable: {env_var_name}")
    return value


class Settings(BaseSettings):
    log_level: str = log_level
    allowed_dirs: Optional[str] = None
    
