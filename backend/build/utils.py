import os
import subprocess
from pathlib import Path
from typing import Tuple, Optional


def run_command(
    command: list,
    cwd: str,
    timeout_seconds: float = 300,
) -> Tuple[bool, str, str]:
    """
    Execute a shell command and return success status, stdout, stderr.
    
    Args:
        command: List of command arguments
        cwd: Working directory for command execution
        
    Returns:
        Tuple of (success: bool, stdout: str, stderr: str)
    """
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        success = result.returncode == 0
        return success, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"Command timed out after {timeout_seconds:.0f} seconds"
    except Exception as e:
        return False, "", str(e)


def get_commit_hash(
    project_path: str,
    timeout_seconds: float = 300,
) -> Optional[str]:
    """
    Get the current commit hash of a git repository.
    
    Args:
        project_path: Path to the git repository
        
    Returns:
        Commit hash string or None if failed
    """
    success, stdout, _ = run_command(
        ["git", "rev-parse", "HEAD"],
        project_path,
        timeout_seconds,
    )
    if success:
        return stdout.strip()
    return None


def ensure_directory_exists(path: str) -> None:
    """
    Ensure a directory exists, create it if it doesn't.
    
    Args:
        path: Directory path to create
    """
    Path(path).mkdir(parents=True, exist_ok=True)


def get_log_path(logs_dir: str, build_id: int) -> str:
    """
    Generate log file path for a build.
    
    Args:
        logs_dir: Directory to store logs
        build_id: Build ID
        
    Returns:
        Full path to log file
    """
    return os.path.join(logs_dir, f"build_{build_id}.log")
