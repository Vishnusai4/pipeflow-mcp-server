import json
from app.constants import APP_FILE_PATH
from typing import List, Dict, Any

def read_app_info() -> List[Dict[str, Any]]:
    """Read Pipedream app info"""
    try:
        with open(APP_FILE_PATH, 'r') as f:
            app_info = json.load(f)
        return app_info
    except Exception as e:
        print(f"Error reading app info: {e}")
        return []
