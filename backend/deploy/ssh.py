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
                key_file = paramiko.RSAKey.from_private_key_file(self.key)
                self.client.connect(
                    hostname=self.host,
                    username=self.username,
                    pkey=key_file,
                    timeout=30
                )
            else:
                # Connect using password
                self.client.connect(
                    hostname=self.host,
                    username=self.username,
                    password=self.password,
                    timeout=30
                )
            
            return True, ""
        except Exception as e:
            return False, f"SSH connection failed: {str(e)}"

    def execute_command(self, command: str) -> Tuple[bool, str, str]:
        """
        Execute a command on the remote server.
        
        Args:
            command: Command to execute
            
        Returns:
            Tuple of (success: bool, stdout: str, stderr: str)
        """
        if not self.client:
            return False, "", "SSH client not connected"
        
        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=300)
            
            # Read output
            stdout_str = stdout.read().decode('utf-8')
            stderr_str = stderr.read().decode('utf-8')
            
            # Get exit status
            exit_status = stdout.channel.recv_exit_status()
            success = exit_status == 0
            
            return success, stdout_str, stderr_str
        except Exception as e:
            return False, "", f"Command execution failed: {str(e)}"

    def close(self):
        """Close SSH connection."""
        if self.client:
            self.client.close()
            self.client = None
