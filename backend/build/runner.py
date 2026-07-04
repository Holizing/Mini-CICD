import os
import sys
from pathlib import Path
from typing import Optional
from backend.build.utils import run_command, get_commit_hash, ensure_directory_exists


class BuildRunner:
    def __init__(self, workspace_dir: str, logs_dir: str):
        self.workspace_dir = workspace_dir
        self.logs_dir = logs_dir
        ensure_directory_exists(workspace_dir)
        ensure_directory_exists(logs_dir)

    def _log(self, log_file, message: str) -> None:
        """Write message to log file."""
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{message}\n")

    def clone_or_pull(self, git_url: str, project_name: str, branch: str, log_file: str) -> tuple[bool, str]:
        """
        Clone repository if not exists, otherwise pull latest changes.
        
        Returns:
            Tuple of (success: bool, error_message: str)
        """
        project_path = os.path.join(self.workspace_dir, project_name)
        
        if not os.path.exists(project_path):
            # Clone repository
            self._log(log_file, f"Cloning repository from {git_url}...")
            success, stdout, stderr = run_command(
                ["git", "clone", git_url, project_name],
                self.workspace_dir
            )
            
            if not success:
                error_msg = f"Git clone failed: {stderr}"
                self._log(log_file, error_msg)
                return False, error_msg
            
            self._log(log_file, f"Repository cloned successfully")
            
            # Checkout branch
            success, stdout, stderr = run_command(["git", "checkout", branch], project_path)
            if not success:
                error_msg = f"Git checkout branch {branch} failed: {stderr}"
                self._log(log_file, error_msg)
                return False, error_msg
        else:
            # Pull latest changes
            self._log(log_file, f"Repository exists, pulling latest changes...")
            
            # Fetch
            success, stdout, stderr = run_command(["git", "fetch"], project_path)
            if not success:
                error_msg = f"Git fetch failed: {stderr}"
                self._log(log_file, error_msg)
                return False, error_msg
            
            # Checkout branch
            success, stdout, stderr = run_command(["git", "checkout", branch], project_path)
            if not success:
                error_msg = f"Git checkout failed: {stderr}"
                self._log(log_file, error_msg)
                return False, error_msg
            
            # Pull
            success, stdout, stderr = run_command(
                ["git", "pull", "origin", branch],
                project_path
            )
            if not success:
                error_msg = f"Git pull failed: {stderr}"
                self._log(log_file, error_msg)
                return False, error_msg
            
            self._log(log_file, f"Repository updated successfully")
        
        return True, ""

    def setup_virtualenv(self, project_path: str, log_file: str) -> tuple[bool, str]:
        """
        Create virtual environment if not exists.
        
        Returns:
            Tuple of (success: bool, error_message: str)
        """
        venv_path = os.path.join(project_path, "venv")
        
        if not os.path.exists(venv_path):
            self._log(log_file, f"Creating virtual environment...")
            success, stdout, stderr = run_command([sys.executable, "-m", "venv", "venv"], project_path)
            
            if not success:
                error_msg = f"Virtual environment creation failed: {stderr}"
                self._log(log_file, error_msg)
                return False, error_msg
            
            self._log(log_file, f"Virtual environment created successfully")
        else:
            self._log(log_file, f"Virtual environment already exists")
        
        return True, ""

    def install_dependencies(self, project_path: str, log_file: str) -> tuple[bool, str]:
        """
        Install dependencies from requirements.txt.
        
        Returns:
            Tuple of (success: bool, error_message: str)
        """
        requirements_path = os.path.join(project_path, "requirements.txt")
        
        if not os.path.exists(requirements_path):
            self._log(log_file, f"No requirements.txt found, skipping dependency installation")
            return True, ""
        
        self._log(log_file, f"Installing dependencies from requirements.txt...")
        
        # Determine pip path based on OS
        if sys.platform == "win32":
            pip_path = os.path.join(project_path, "venv", "Scripts", "pip")
        else:
            pip_path = os.path.join(project_path, "venv", "bin", "pip")
        
        success, stdout, stderr = run_command([pip_path, "install", "-r", "requirements.txt"], project_path)
        
        if not success:
            error_msg = f"Dependency installation failed: {stderr}"
            self._log(log_file, error_msg)
            return False, error_msg
        
        self._log(log_file, f"Dependencies installed successfully")
        self._log(log_file, stdout)
        
        return True, ""

    def run_build(self, project_path: str, log_file: str) -> tuple[bool, str]:
        """
        Run build command (python -m compileall .).
        
        Returns:
            Tuple of (success: bool, error_message: str)
        """
        self._log(log_file, f"Running build command: python -m compileall .")
        
        # Use system Python for compilation
        success, stdout, stderr = run_command([sys.executable, "-m", "compileall", "."], project_path)
        
        self._log(log_file, stdout)
        if stderr:
            self._log(log_file, f"Build stderr: {stderr}")
        
        if not success:
            error_msg = f"Build failed: {stderr}"
            self._log(log_file, error_msg)
            return False, error_msg
        
        self._log(log_file, f"Build completed successfully")
        
        return True, ""

    def execute_build(
        self,
        git_url: str,
        project_name: str,
        branch: str,
        build_id: int
    ) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Execute the complete build pipeline.
        
        Returns:
            Tuple of (success: bool, commit_hash: str, error_message: str)
        """
        log_file = os.path.join(self.logs_dir, f"build_{build_id}.log")
        project_path = os.path.join(self.workspace_dir, project_name)
        
        self._log(log_file, f"=== Build #{build_id} Started ===")
        self._log(log_file, f"Project: {project_name}")
        self._log(log_file, f"Branch: {branch}")
        self._log(log_file, f"Git URL: {git_url}")
        
        # Step 1: Clone or Pull
        success, error = self.clone_or_pull(git_url, project_name, branch, log_file)
        if not success:
            return False, None, error
        
        # Step 2: Get commit hash
        commit_hash = get_commit_hash(project_path)
        if commit_hash:
            self._log(log_file, f"Current commit: {commit_hash}")
        else:
            self._log(log_file, f"Warning: Could not get commit hash")
        
        # Step 3: Setup virtual environment
        success, error = self.setup_virtualenv(project_path, log_file)
        if not success:
            return False, commit_hash, error
        
        # Step 4: Install dependencies
        success, error = self.install_dependencies(project_path, log_file)
        if not success:
            return False, commit_hash, error
        
        # Step 5: Run build
        success, error = self.run_build(project_path, log_file)
        if not success:
            return False, commit_hash, error
        
        self._log(log_file, f"=== Build #{build_id} Completed Successfully ===")
        
        return True, commit_hash, ""
