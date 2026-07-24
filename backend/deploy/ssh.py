import paramiko
from typing import Tuple, Optional


class SSHClient:
    def __init__(self, host: str, username: str, password: Optional[str] = None, key: Optional[str] = None):
        self.host = host
        self.username = username
        self.password = password
        self.key = key
        self.client = None

    def connect(self) -> Tuple[bool, str]:
        """
        Establish SSH connection.

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            if self.key:
                # Connect using SSH key
                import os
                if not os.path.exists(self.key):
                    return False, f"SSH key file not found: {self.key}"
                key_file = paramiko.RSAKey.from_private_key_file(self.key)
                self.client.connect(
                    hostname=self.host,
                    username=self.username,
                    pkey=key_file,
                    timeout=60,  # Increased from 30 to 60 seconds
                    auth_timeout=60,
                    banner_timeout=30
                )
            else:
                # Connect using password
                if not self.password:
                    return False, "SSH password not provided"
                self.client.connect(
                    hostname=self.host,
                    username=self.username,
                    password=self.password,
                    timeout=60,  # Increased from 30 to 60 seconds
                    auth_timeout=60,
                    banner_timeout=30
                )

            return True, ""
        except paramiko.AuthenticationException as e:
            return False, f"SSH authentication failed: {str(e)}"
        except paramiko.SSHException as e:
            return False, f"SSH connection error: {str(e)}"
        except Exception as e:
            return False, f"SSH connection failed: {str(e)}"

    def execute_command(self, command: str, use_pty: bool = False) -> Tuple[bool, str, str]:
        """
        Execute a command on the remote server.

        Args:
            command: Command to execute
            use_pty: Whether to allocate a pseudo-terminal (default: False)

        Returns:
            Tuple of (success: bool, stdout: str, stderr: str)
        """
        print(f"[SSH] Executing command: {command}")
        print(f"[SSH] use_pty: {use_pty}")
        
        if not self.client:
            print(f"[SSH] ERROR: SSH client not connected")
            return False, "", "SSH client not connected"

        try:
            # Automatically add -n flag to sudo commands for passwordless sudo
            # This prevents sudo from prompting for password even if NOPASSWD is configured
            original_command = command
            if 'sudo' in command and '-n' not in command.split():
                # Insert -n after sudo (e.g., "sudo systemctl" -> "sudo -n systemctl")
                command = command.replace('sudo', 'sudo -n', 1)
                print(f"[SSH] Modified command with -n flag: {command}")
            else:
                print(f"[SSH] Command unchanged (no sudo or already has -n): {command}")

            # Only use PTY if explicitly requested (for interactive commands)
            # For simple commands, PTY is not needed and can cause hanging
            stdin, stdout, stderr = self.client.exec_command(command, timeout=300, get_pty=use_pty)

            # Read output
            stdout_str = stdout.read().decode('utf-8')
            stderr_str = stderr.read().decode('utf-8')

            # Get exit status
            exit_status = stdout.channel.recv_exit_status()
            success = exit_status == 0

            print(f"[SSH] Command completed: exit_status={exit_status}, success={success}")
            if stdout_str:
                print(f"[SSH] stdout: {stdout_str[:200]}")  # Log first 200 chars
            if stderr_str:
                print(f"[SSH] stderr: {stderr_str[:200]}")  # Log first 200 chars
            
            return success, stdout_str, stderr_str
        except Exception as e:
            print(f"[SSH] Exception in execute_command: {str(e)}")
            import traceback
            print(f"[SSH] Traceback: {traceback.format_exc()}")
            return False, "", f"Command execution failed: {str(e)}"

    def upload_file(self, local_path: str, remote_path: str) -> Tuple[bool, str]:
        """
        Upload a file to the remote server using SFTP.

        Args:
            local_path: Path to the local file
            remote_path: Path to the remote file

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        if not self.client:
            return False, "SSH client not connected"

        try:
            sftp = self.client.open_sftp()
            sftp.put(local_path, remote_path)
            sftp.close()
            return True, ""
        except Exception as e:
            return False, f"File upload failed: {str(e)}"

    def upload_directory(self, local_dir: str, remote_dir: str) -> Tuple[bool, str]:
        """
        Upload a directory to the remote server using SFTP.

        Args:
            local_dir: Path to the local directory
            remote_dir: Path to the remote directory

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        if not self.client:
            return False, "SSH client not connected"

        import os

        # Exclude directories from upload (dependencies, cache, etc.)
        exclude_dirs = {'.git', 'node_modules', 'venv', '__pycache__', 'target', 'build', 'dist', 'coverage', 'vendor', '.next', '.venv', 'tmp', 'cache', 'logs', '.idea', '.vscode'}

        try:
            # Check if local directory exists
            if not os.path.exists(local_dir):
                return False, f"Local directory does not exist: {local_dir}"
            if not os.path.isdir(local_dir):
                return False, f"Local path is not a directory: {local_dir}"

            sftp = self.client.open_sftp()

            # Create remote directory if it doesn't exist
            try:
                sftp.stat(remote_dir)
            except IOError:
                # Directory doesn't exist, create it recursively
                self._mkdir_recursive(sftp, remote_dir)

            # First pass: create all directory structure
            for root, dirs, files in os.walk(local_dir):
                # Exclude unwanted directories
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                
                # Calculate relative path
                rel_path = os.path.relpath(root, local_dir)
                if rel_path == '.':
                    remote_path = remote_dir
                else:
                    remote_path = os.path.join(remote_dir, rel_path).replace('\\', '/')
                    # Ensure the remote subdirectory exists
                    try:
                        sftp.stat(remote_path)
                    except IOError:
                        self._mkdir_recursive(sftp, remote_path)

                # Create subdirectories
                for dir_name in dirs:
                    full_remote_dir = os.path.join(remote_path, dir_name).replace('\\', '/')
                    try:
                        sftp.stat(full_remote_dir)
                    except IOError:
                        self._mkdir_recursive(sftp, full_remote_dir)

            # Second pass: upload all files
            for root, dirs, files in os.walk(local_dir):
                # Exclude unwanted directories
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                
                # Calculate relative path
                rel_path = os.path.relpath(root, local_dir)
                print(f"[DEBUG] rel_path = {rel_path}")
                if rel_path == '.':
                    remote_path = remote_dir
                    print(f"[DEBUG] remote_path = {remote_path} (root)")
                else:
                    remote_path = os.path.join(remote_dir, rel_path).replace('\\', '/')
                    print(f"[DEBUG] remote_path = {remote_path} (subdir)")

                # Upload files
                for file_name in files:
                    local_file = os.path.join(root, file_name)
                    remote_file = os.path.join(remote_path, file_name).replace('\\', '/')
                    
                    print(f"[DEBUG] local_file = {local_file}")
                    print(f"[DEBUG] remote_file = {remote_file}")
                    
                    # Check remote parent directory
                    import posixpath
                    remote_parent = posixpath.dirname(remote_file)
                    print(f"[DEBUG] remote_parent = {remote_parent}")
                    
                    try:
                        sftp.stat(remote_parent)
                        print(f"[DEBUG] remote_parent exists: {repr(remote_parent)}")
                    except IOError as e:
                        print(f"[DEBUG] remote_parent does not exist: {repr(remote_parent)}")
                        print(f"[DEBUG] Creating remote_parent: {repr(remote_parent)}")
                        self._mkdir_recursive(sftp, remote_parent)
                        print(f"[DEBUG] remote_parent creation completed, verifying: {repr(remote_parent)}")
                        # Verify it was actually created
                        try:
                            sftp.stat(remote_parent)
                            print(f"[DEBUG] remote_parent verified exists: {repr(remote_parent)}")
                        except IOError as e:
                            print(f"[DEBUG] remote_parent still does not exist after creation: {repr(remote_parent)}")
                            print(f"[DEBUG] Error: {str(e)}")
                            raise Exception(f"Failed to create remote_parent {repr(remote_parent)}")
                    
                    print(f"[DEBUG] Uploading file: {local_file} -> {remote_file}")
                    print(f"[DEBUG] Final verification before upload: {repr(remote_file)}")
                    sftp.put(local_file, remote_file)
                    print(f"[DEBUG] File uploaded successfully")

            sftp.close()
            return True, ""
        except Exception as e:
            import traceback
            return False, f"Directory upload failed: {str(e)}\nTraceback:\n{traceback.format_exc()}"

    def _mkdir_recursive(self, sftp, path: str):
        """
        Recursively create directories on remote server.

        Args:
            sftp: SFTP client
            path: Path to create
        """
        print(f"[DEBUG] ENTER _mkdir_recursive: {repr(path)}")
        import posixpath
        dirs = [d for d in path.split('/') if d]  # Filter out empty strings
        print(f"[DEBUG] Split path: {dirs}")
        current_dir = ''
        for dir_name in dirs:
            # Use posixpath.join to properly construct absolute paths
            current_dir = posixpath.join(current_dir, dir_name) if current_dir else '/' + dir_name
            print(f"[DEBUG] Checking: {repr(current_dir)}")
            try:
                sftp.stat(current_dir)
                print(f"[DEBUG] Exists: {repr(current_dir)}")
            except IOError:
                print(f"[DEBUG] Creating: {repr(current_dir)}")
                try:
                    sftp.mkdir(current_dir)
                    print(f"[DEBUG] mkdir() returned for: {repr(current_dir)}")
                    # Verify it was actually created
                    sftp.stat(current_dir)
                    print(f"[DEBUG] Verified created: {repr(current_dir)}")
                except Exception as e:
                    print(f"[DEBUG] Failed to create {repr(current_dir)}: {str(e)}")
                    import traceback
                    print(f"[DEBUG] Traceback: {traceback.format_exc()}")
                    raise
        print(f"[DEBUG] EXIT _mkdir_recursive: {repr(path)}")

    def close(self):
        """Close SSH connection."""
        if self.client:
            self.client.close()
            self.client = None
