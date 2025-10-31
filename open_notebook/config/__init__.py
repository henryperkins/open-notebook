"""Configuration package for Open Notebook."""

# Import configuration from the main config module
import os
import sys

# Add the parent directory to path so we can import the config module
parent_dir = os.path.dirname(os.path.dirname(__file__))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import the actual config variables
import importlib.util
from types import ModuleType

config_path = os.path.join(parent_dir, "config.py")
spec = importlib.util.spec_from_file_location("open_notebook_config", config_path)
if spec is None or spec.loader is None:
    raise ImportError(f"Unable to load configuration module at {config_path}")

config_module = importlib.util.module_from_spec(spec)
assert isinstance(config_module, ModuleType)
spec.loader.exec_module(config_module)

# Export all the config variables
UPLOADS_FOLDER = config_module.UPLOADS_FOLDER
TIKTOKEN_CACHE_DIR = config_module.TIKTOKEN_CACHE_DIR
DATA_FOLDER = config_module.DATA_FOLDER
LANGGRAPH_CHECKPOINT_FILE = config_module.LANGGRAPH_CHECKPOINT_FILE

# Also make available via attributes
__all__ = ['UPLOADS_FOLDER', 'TIKTOKEN_CACHE_DIR', 'DATA_FOLDER', 'LANGGRAPH_CHECKPOINT_FILE']
