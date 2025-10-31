"""Configuration package for Open Notebook."""

# Import configuration from the main config module
import sys
import os

# Add the parent directory to path so we can import the config module
parent_dir = os.path.dirname(os.path.dirname(__file__))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import the actual config variables
import importlib.util
spec = importlib.util.spec_from_file_location("open_notebook_config", os.path.join(parent_dir, "config.py"))
config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config_module)

# Export all the config variables
UPLOADS_FOLDER = config_module.UPLOADS_FOLDER
TIKTOKEN_CACHE_DIR = config_module.TIKTOKEN_CACHE_DIR
DATA_FOLDER = config_module.DATA_FOLDER
LANGGRAPH_CHECKPOINT_FILE = config_module.LANGGRAPH_CHECKPOINT_FILE

# Also make available via attributes
__all__ = ['UPLOADS_FOLDER', 'TIKTOKEN_CACHE_DIR', 'DATA_FOLDER', 'LANGGRAPH_CHECKPOINT_FILE']
