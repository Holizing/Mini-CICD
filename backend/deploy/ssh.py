"""Deadline-aware SSH client with strict host-key verification."""

import os
import posixpath
import time
from typing import Optional, Tuple

import paramiko


class SSHClient:
    def __init__(
        self,
        host: str,
        username: str,
        password: Optional[str] = None,
        key: Optional[str] = None,
        timeout_seconds: int = 600,
        deadline: Optional[float] = None,
        known_hosts_path: Optional[str] = None,
    ):
        self.host = host
        self.username = username
        self.password = password
        self.key = key
        self.timeout_seconds = timeout_seconds
        self.deadline = deadline or (time.monotonic() + timeout_seconds)
        self.known_hosts_path = (
            known_hosts_path
            or os.getenv("MINI_CICD_SSH_KNOWN_HOSTS")
        )
        self.client = None

    def _remaining_timeout(self) -> float:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(
                f"Deploy timed out after {self.timeout_seconds} seconds"
            )
        return max(0.1, remaining)

    def _open_sftp(self):
        if self.client is None:
            raise RuntimeError("SSH client not connected")
        sftp = self.client.open_sftp()
        sftp.get_channel().settimeout(self._remaining_timeout())
        return sftp

    def connect(self) -> Tuple[bool, str]:
        """Connect only when the server key already exists in known_hosts."""
        try:
            self.client = paramiko.SSHClient()
            if self.known_hosts_path:
                known_hosts = os.path.abspath(
                    os.path.expanduser(self.known_hosts_path)
                )
                if not os.path.isfile(known_hosts):
                    return (
                        False,
                        f"SSH known_hosts file not found: {known_hosts}",
                    )
                self.client.load_system_host_keys(known_hosts)
            else:
                self.client.load_system_host_keys()
            self.client.set_missing_host_key_policy(paramiko.RejectPolicy())

            connection_timeout = min(60.0, self._remaining_timeout())
            banner_timeout = min(30.0, connection_timeout)
            connect_options = {
                "hostname": self.host,
                "username": self.username,
                "timeout": connection_timeout,
                "auth_timeout": connection_timeout,
                "banner_timeout": banner_timeout,
            }

            if self.key:
                key_path = os.path.abspath(os.path.expanduser(self.key))
                if not os.path.isfile(key_path):
                    return False, f"SSH key file not found: {key_path}"
                connect_options["pkey"] = (
                    paramiko.RSAKey.from_private_key_file(key_path)
                )
            elif self.password:
                connect_options["password"] = self.password
            else:
                return False, "SSH password or key is required"

            self.client.connect(**connect_options)
            return True, ""
        except paramiko.BadHostKeyException:
            return False, "SSH host key does not match known_hosts"
        except paramiko.AuthenticationException:
            return False, "SSH authentication failed"
        except paramiko.SSHException as error:
            return False, f"SSH connection error: {error}"
        except Exception as error:
            return False, f"SSH connection failed: {error}"

    def execute_command(
        self,
        command: str,
        use_pty: bool = False,
    ) -> Tuple[bool, str, str]:
        if self.client is None:
            return False, "", "SSH client not connected"

        try:
            _, stdout, stderr = self.client.exec_command(
                command,
                timeout=self._remaining_timeout(),
                get_pty=use_pty,
            )
            stdout_text = stdout.read().decode("utf-8", errors="replace")
            stderr_text = stderr.read().decode("utf-8", errors="replace")
            exit_status = stdout.channel.recv_exit_status()
            return exit_status == 0, stdout_text, stderr_text
        except Exception as error:
            return False, "", f"Command execution failed: {error}"

    def upload_file(
        self,
        local_path: str,
        remote_path: str,
    ) -> Tuple[bool, str]:
        if self.client is None:
            return False, "SSH client not connected"

        sftp = None
        try:
            sftp = self._open_sftp()
            sftp.put(local_path, remote_path)
            return True, ""
        except Exception as error:
            return False, f"File upload failed: {error}"
        finally:
            if sftp is not None:
                sftp.close()

    def upload_directory(
        self,
        local_dir: str,
        remote_dir: str,
    ) -> Tuple[bool, str]:
        if self.client is None:
            return False, "SSH client not connected"
        if not os.path.isdir(local_dir):
            return False, f"Local directory does not exist: {local_dir}"

        excluded_directories = {
            ".git",
            ".idea",
            ".next",
            ".venv",
            ".vscode",
            "__pycache__",
            "cache",
            "coverage",
            "logs",
            "node_modules",
            "tmp",
            "venv",
            "vendor",
        }

        sftp = None
        try:
            sftp = self._open_sftp()
            self._mkdir_recursive(sftp, remote_dir)

            for root, directories, files in os.walk(local_dir):
                directories[:] = [
                    directory
                    for directory in directories
                    if directory not in excluded_directories
                ]
                relative_root = os.path.relpath(root, local_dir)
                remote_root = (
                    remote_dir
                    if relative_root == "."
                    else posixpath.join(
                        remote_dir,
                        relative_root.replace("\\", "/"),
                    )
                )
                self._mkdir_recursive(sftp, remote_root)

                for directory in directories:
                    self._mkdir_recursive(
                        sftp,
                        posixpath.join(remote_root, directory),
                    )
                for filename in files:
                    local_file = os.path.join(root, filename)
                    remote_file = posixpath.join(remote_root, filename)
                    sftp.put(local_file, remote_file)
            return True, ""
        except Exception as error:
            return False, f"Directory upload failed: {error}"
        finally:
            if sftp is not None:
                sftp.close()

    def _mkdir_recursive(self, sftp, path: str) -> None:
        normalized = posixpath.normpath(path)
        if not normalized.startswith("/") or ".." in normalized.split("/"):
            raise ValueError("Remote SFTP path must be absolute and safe")

        current = "/"
        for component in [part for part in normalized.split("/") if part]:
            current = posixpath.join(current, component)
            try:
                sftp.stat(current)
            except IOError:
                sftp.mkdir(current)

    def close(self) -> None:
        if self.client is not None:
            self.client.close()
            self.client = None
