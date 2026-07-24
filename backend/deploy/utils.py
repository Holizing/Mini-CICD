import os
from pathlib import Path


def ensure_directory_exists(path: str) -> None:
    """
    Ensure a directory exists, create it if it doesn't.
    
    Args:
        path: Directory path to create
    """
    Path(path).mkdir(parents=True, exist_ok=True)


def get_log_path(logs_dir: str, deploy_id: int) -> str:
    """
    Generate log file path for a deploy.
    
    Args:
        logs_dir: Directory to store logs
        deploy_id: Deploy ID
        
    Returns:
        Full path to log file
    """
    return os.path.join(logs_dir, f"deploy_{deploy_id}.log")
