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

    def execute_command(self, command: str, use_pty: bool = False, sudo_password: Optional[str] = None) -> Tuple[bool, str, str]:
        """
        Execute a command on the remote server.

        Args:
            command: Command to execute
            use_pty: Whether to allocate a pseudo-terminal (default: False)
            sudo_password: Password to use for sudo commands (optional)

        Returns:
            Tuple of (success: bool, stdout: str, stderr: str)
        """
        if not self.client:
            return False, "", "SSH client not connected"

        try:
            # Only use PTY if explicitly requested (for interactive commands)
            # For simple commands like sudo cp, PTY is not needed and can cause hanging
            stdin, stdout, stderr = self.client.exec_command(command, timeout=300, get_pty=use_pty)

            # If command uses sudo and password is provided, send it to stdin
            if sudo_password and 'sudo' in command:
                stdin.write(sudo_password + '\n')
                stdin.flush()

            # Read output
            stdout_str = stdout.read().decode('utf-8')
            stderr_str = stderr.read().decode('utf-8')

            # Get exit status
            exit_status = stdout.channel.recv_exit_status()
            success = exit_status == 0

            return success, stdout_str, stderr_str
        except Exception as e:
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

        try:
            sftp = self.client.open_sftp()

            # Create remote directory if it doesn't exist
            try:
                sftp.stat(remote_dir)
            except IOError:
                # Directory doesn't exist, create it recursively
                self._mkdir_recursive(sftp, remote_dir)

            # Upload all files in directory
            for root, dirs, files in os.walk(local_dir):
                # Calculate relative path
                rel_path = os.path.relpath(root, local_dir)
                if rel_path == '.':
                    remote_path = remote_dir
                else:
                    remote_path = os.path.join(remote_dir, rel_path).replace('\\', '/')

                # Create subdirectories
                for dir_name in dirs:
                    full_remote_dir = os.path.join(remote_path, dir_name).replace('\\', '/')
                    try:
                        sftp.stat(full_remote_dir)
                    except IOError:
                        sftp.mkdir(full_remote_dir)

                # Upload files
                for file_name in files:
                    local_file = os.path.join(root, file_name)
                    remote_file = os.path.join(remote_path, file_name).replace('\\', '/')
                    sftp.put(local_file, remote_file)

            sftp.close()
            return True, ""
        except Exception as e:
            return False, f"Directory upload failed: {str(e)}"

    def _mkdir_recursive(self, sftp, path: str):
        """
        Recursively create directories on remote server.

        Args:
            sftp: SFTP client
            path: Path to create
        """
        import os
        dirs = path.split('/')
        current_dir = ''
        for dir_name in dirs:
            if dir_name:
                current_dir += '/' + dir_name if current_dir else dir_name
                try:
                    sftp.stat(current_dir)
                except IOError:
                    sftp.mkdir(current_dir)

    def close(self):
        """Close SSH connection."""
        if self.client:
            self.client.close()
            self.client = None
