"""Validated artifact transfer and atomic remote release helpers."""

from dataclasses import dataclass
import json
import os
import posixpath
import re
import shlex
from typing import Callable, Optional


class DeploymentSafetyError(ValueError):
    """Raised when deployment input or a remote operation is unsafe."""


_REMOTE_PATH_PATTERN = re.compile(r"^/[A-Za-z0-9._/-]+$")
_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.@-]{0,127}$")
_PROJECT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,127}$")
_REMOTE_HOST_PATTERN = re.compile(r"^[A-Za-z0-9.:[\]-]+$")
_REMOTE_USER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]{0,63}\$?$")
_HEALTH_PATH_PATTERN = re.compile(r"^/[A-Za-z0-9._~/%=-]*$")
_PORT_MAPPING_PATTERN = re.compile(r"^([0-9]{1,5}):([0-9]{1,5})$")
_DOCKER_IMAGE_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._/@:-]{0,254}$"
)


def validate_remote_deploy_path(deploy_path: str) -> str:
    """Return a normalized, non-root absolute POSIX deployment path."""
    if not deploy_path or not deploy_path.strip():
        raise DeploymentSafetyError("Deploy path is required")

    raw_path = deploy_path.strip()
    if any(ord(character) < 32 for character in raw_path):
        raise DeploymentSafetyError(
            "Deploy path contains control characters"
        )
    if not raw_path.startswith("/"):
        raise DeploymentSafetyError("Deploy path must be absolute")
    if ".." in raw_path.split("/"):
        raise DeploymentSafetyError(
            "Deploy path cannot contain parent traversal"
        )
    if not _REMOTE_PATH_PATTERN.fullmatch(raw_path):
        raise DeploymentSafetyError(
            "Deploy path contains unsupported shell characters"
        )

    normalized_path = "/" + posixpath.normpath(raw_path).lstrip("/")
    if normalized_path == "/":
        raise DeploymentSafetyError(
            "Deploy path cannot be the filesystem root"
        )
    return normalized_path


def validate_identifier(value: str, label: str) -> str:
    normalized = (value or "").strip()
    if not _IDENTIFIER_PATTERN.fullmatch(normalized):
        raise DeploymentSafetyError(
            f"{label} must contain only letters, numbers, '.', '_', '@', or '-'"
        )
    return normalized


def validate_project_name(value: str) -> str:
    normalized = (value or "").strip()
    if not _PROJECT_NAME_PATTERN.fullmatch(normalized):
        raise DeploymentSafetyError(
            "Project name contains unsupported shell characters"
        )
    return normalized


def validate_remote_host(value: str) -> str:
    normalized = (value or "").strip()
    if not _REMOTE_HOST_PATTERN.fullmatch(normalized):
        raise DeploymentSafetyError("Server host is invalid")
    return normalized


def validate_remote_user(value: str) -> str:
    normalized = (value or "").strip()
    if not _REMOTE_USER_PATTERN.fullmatch(normalized):
        raise DeploymentSafetyError("Server user is invalid")
    return normalized


def validate_health_check_path(value: Optional[str]) -> str:
    path = (value or "/").strip()
    if not _HEALTH_PATH_PATTERN.fullmatch(path):
        raise DeploymentSafetyError("Health check path is invalid")
    return path


def validate_port_mapping(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    match = _PORT_MAPPING_PATTERN.fullmatch(value.strip())
    if not match:
        raise DeploymentSafetyError(
            "Port mapping must use host_port:container_port"
        )
    ports = [int(match.group(1)), int(match.group(2))]
    if any(port < 1 or port > 65535 for port in ports):
        raise DeploymentSafetyError("Port mapping contains an invalid port")
    return value.strip()


def validate_docker_image(value: str) -> str:
    normalized = (value or "").strip()
    if not _DOCKER_IMAGE_PATTERN.fullmatch(normalized):
        raise DeploymentSafetyError("Docker image reference is invalid")
    return normalized


def resolve_artifact_path(
    artifact_path: str,
    workspace_dir: Optional[str] = None,
) -> str:
    """Resolve an artifact and keep relative artifacts inside the workspace."""
    if not artifact_path or not artifact_path.strip():
        raise DeploymentSafetyError("Artifact path is required")

    workspace_root = os.path.realpath(workspace_dir or os.getcwd())
    if os.path.isabs(artifact_path):
        resolved_path = os.path.realpath(artifact_path)
    else:
        resolved_path = os.path.realpath(
            os.path.join(workspace_root, artifact_path)
        )
        if os.path.commonpath([workspace_root, resolved_path]) != workspace_root:
            raise DeploymentSafetyError(
                "Artifact path escapes the workspace"
            )

    if not os.path.exists(resolved_path):
        raise DeploymentSafetyError(
            f"Artifact does not exist: {resolved_path}"
        )
    return resolved_path


def run_checked(ssh_client, command: str, action: str) -> str:
    success, stdout, stderr = ssh_client.execute_command(command)
    if not success:
        detail = (stderr or stdout or "remote command failed").strip()
        raise DeploymentSafetyError(f"{action}: {detail}")
    return stdout


def transfer_artifact(
    ssh_client,
    artifact_path: str,
    artifact_type: Optional[str],
    remote_directory: str,
    log_func: Callable[[str], None],
    *,
    workspace_dir: Optional[str] = None,
) -> str:
    """Upload a directory's contents or a file into a validated directory."""
    local_path = resolve_artifact_path(artifact_path, workspace_dir)
    remote_directory = validate_remote_deploy_path(remote_directory)
    is_directory = os.path.isdir(local_path)

    if artifact_type == "directory" and not is_directory:
        raise DeploymentSafetyError(
            f"Artifact is marked as a directory but is not one: {local_path}"
        )
    if artifact_type in {"file", "jar", "war"} and is_directory:
        raise DeploymentSafetyError(
            f"Artifact is marked as a file but is a directory: {local_path}"
        )

    run_checked(
        ssh_client,
        f"mkdir -p -- {shlex.quote(remote_directory)}",
        "Failed to create remote artifact directory",
    )

    if is_directory:
        log_func(f"Uploading directory artifact to {remote_directory}")
        success, error = ssh_client.upload_directory(
            local_path,
            remote_directory,
        )
        remote_artifact_path = remote_directory
    else:
        artifact_name = validate_identifier(
            os.path.basename(local_path),
            "Artifact filename",
        )
        remote_artifact_path = posixpath.join(
            remote_directory,
            artifact_name,
        )
        log_func(f"Uploading file artifact to {remote_artifact_path}")
        success, error = ssh_client.upload_file(
            local_path,
            remote_artifact_path,
        )

    if not success:
        raise DeploymentSafetyError(f"Artifact upload failed: {error}")
    return remote_artifact_path


@dataclass(frozen=True)
class RemoteRelease:
    deploy_path: str
    release_id: str
    releases_path: str
    release_path: str
    current_path: str
    previous_target: Optional[str]

    @classmethod
    def prepare(
        cls,
        ssh_client,
        deploy_path: str,
        release_id: str,
    ) -> "RemoteRelease":
        safe_deploy_path = validate_remote_deploy_path(deploy_path)
        safe_release_id = validate_identifier(release_id, "Release ID")
        releases_path = posixpath.join(safe_deploy_path, "releases")
        release_path = posixpath.join(releases_path, safe_release_id)
        current_path = posixpath.join(safe_deploy_path, "current")

        previous_success, previous_stdout, _ = ssh_client.execute_command(
            f"readlink -f -- {shlex.quote(current_path)}"
        )
        previous_target = (
            previous_stdout.strip()
            if previous_success and previous_stdout.strip()
            else None
        )

        run_checked(
            ssh_client,
            " && ".join(
                [
                    f"mkdir -p -- {shlex.quote(releases_path)}",
                    f"rm -rf -- {shlex.quote(release_path)}",
                    f"mkdir -p -- {shlex.quote(release_path)}",
                ]
            ),
            "Failed to prepare release directory",
        )
        return cls(
            deploy_path=safe_deploy_path,
            release_id=safe_release_id,
            releases_path=releases_path,
            release_path=release_path,
            current_path=current_path,
            previous_target=previous_target,
        )

    def activate(self, ssh_client) -> None:
        next_link = f"{self.current_path}.next"
        run_checked(
            ssh_client,
            " && ".join(
                [
                    f"rm -f -- {shlex.quote(next_link)}",
                    (
                        f"ln -s -- {shlex.quote(self.release_path)} "
                        f"{shlex.quote(next_link)}"
                    ),
                    (
                        f"mv -Tf -- {shlex.quote(next_link)} "
                        f"{shlex.quote(self.current_path)}"
                    ),
                ]
            ),
            "Failed to activate release",
        )

    def rollback(self, ssh_client) -> None:
        next_link = f"{self.current_path}.rollback"
        if self.previous_target:
            previous_target = validate_remote_deploy_path(
                self.previous_target
            )
            run_checked(
                ssh_client,
                " && ".join(
                    [
                        f"rm -f -- {shlex.quote(next_link)}",
                        (
                            f"ln -s -- {shlex.quote(previous_target)} "
                            f"{shlex.quote(next_link)}"
                        ),
                        (
                            f"mv -Tf -- {shlex.quote(next_link)} "
                            f"{shlex.quote(self.current_path)}"
                        ),
                    ]
                ),
                "Failed to restore previous release",
            )
        else:
            run_checked(
                ssh_client,
                f"rm -f -- {shlex.quote(self.current_path)}",
                "Failed to remove new release link",
            )

    def discard(self, ssh_client) -> None:
        run_checked(
            ssh_client,
            f"rm -rf -- {shlex.quote(self.release_path)}",
            "Failed to discard release",
        )

    def prune(self, ssh_client, keep: int = 5) -> None:
        if keep < 1:
            raise DeploymentSafetyError("At least one release must be kept")
        run_checked(
            ssh_client,
            (
                f"cd {shlex.quote(self.releases_path)} && "
                "ls -1dt -- */ 2>/dev/null | "
                f"tail -n +{keep + 1} | "
                "xargs -r rm -rf --"
            ),
            "Failed to prune old releases",
        )


def install_user_service(
    ssh_client,
    service_name: str,
    unit_content: str,
) -> None:
    service_name = validate_identifier(service_name, "Service name")
    unit_path = f"$HOME/.config/systemd/user/{service_name}.service"
    run_checked(
        ssh_client,
        (
            'mkdir -p -- "$HOME/.config/systemd/user" && '
            f"printf %s {shlex.quote(unit_content)} > "
            f'"{unit_path}" && '
            "systemctl --user daemon-reload"
        ),
        "Failed to install user systemd service",
    )


def restart_user_service(ssh_client, service_name: str) -> None:
    service_name = validate_identifier(service_name, "Service name")
    run_checked(
        ssh_client,
        (
            f"systemctl --user enable {shlex.quote(service_name)}.service "
            f"&& systemctl --user restart {shlex.quote(service_name)}.service"
        ),
        "Failed to restart user service",
    )


def user_service_is_active(ssh_client, service_name: str) -> bool:
    service_name = validate_identifier(service_name, "Service name")
    success, stdout, _ = ssh_client.execute_command(
        f"systemctl --user is-active {shlex.quote(service_name)}.service"
    )
    return success and stdout.strip() == "active"


def http_health_check(
    ssh_client,
    port: int,
    path: Optional[str],
) -> bool:
    if port < 1 or port > 65535:
        raise DeploymentSafetyError("Health check port is invalid")
    safe_path = validate_health_check_path(path)
    url = f"http://127.0.0.1:{port}{safe_path}"
    success, _, _ = ssh_client.execute_command(
        "curl --fail --silent --show-error --max-time 10 "
        f"{shlex.quote(url)}"
    )
    return success


def wait_for_http_health(
    ssh_client,
    port: int,
    path: Optional[str],
    timeout_seconds: float = 30,
    poll_interval_seconds: float = 1,
) -> bool:
    """Poll an HTTP endpoint remotely until it is healthy."""
    if port < 1 or port > 65535:
        raise DeploymentSafetyError("Health check port is invalid")
    safe_path = validate_health_check_path(path)
    retries = max(0, int(timeout_seconds / poll_interval_seconds) - 1)
    retry_delay = max(1, int(poll_interval_seconds))
    url = f"http://127.0.0.1:{port}{safe_path}"
    success, _, _ = ssh_client.execute_command(
        "curl --fail --silent --show-error "
        f"--retry {retries} --retry-delay {retry_delay} "
        "--retry-connrefused "
        f"--retry-max-time {max(1, int(timeout_seconds))} "
        "--max-time 5 "
        f"{shlex.quote(url)}"
    )
    return success


def wait_for_user_service_health(
    ssh_client,
    service_name: str,
    port: int,
    path: Optional[str],
    timeout_seconds: float = 30,
    poll_interval_seconds: float = 1,
) -> bool:
    """Wait for both a user service and its HTTP endpoint to become ready."""
    service_name = validate_identifier(service_name, "Service name")
    attempts = max(1, int(timeout_seconds / poll_interval_seconds))
    retry_delay = max(1, int(poll_interval_seconds))
    service_success, _, _ = ssh_client.execute_command(
        f"for attempt in $(seq 1 {attempts}); do "
        "systemctl --user is-active --quiet "
        f"{shlex.quote(service_name)}.service && exit 0; "
        f"sleep {retry_delay}; "
        "done; exit 1"
    )
    return service_success and wait_for_http_health(
        ssh_client,
        port,
        path,
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
    )


def validate_express_artifact(artifact_path: str) -> None:
    package_path = os.path.join(artifact_path, "package.json")
    lock_path = os.path.join(artifact_path, "package-lock.json")
    if not os.path.isfile(package_path) or not os.path.isfile(lock_path):
        raise DeploymentSafetyError(
            "Express artifact requires package.json and package-lock.json"
        )
    with open(package_path, "r", encoding="utf-8") as package_file:
        package_data = json.load(package_file)
    if not package_data.get("scripts", {}).get("start"):
        raise DeploymentSafetyError(
            "Express package.json requires a start script"
        )


def validate_fastapi_artifact(artifact_path: str) -> None:
    requirements_path = os.path.join(artifact_path, "requirements.txt")
    entrypoint_path = os.path.join(artifact_path, "main.py")
    if not os.path.isfile(requirements_path):
        raise DeploymentSafetyError(
            "FastAPI artifact requires requirements.txt"
        )
    if not os.path.isfile(entrypoint_path):
        raise DeploymentSafetyError(
            "FastAPI verified profile requires main.py with main:app"
        )

    with open(requirements_path, "r", encoding="utf-8") as requirements_file:
        requirements = [
            line.strip()
            for line in requirements_file
            if line.strip() and not line.lstrip().startswith("#")
        ]
    unpinned = [
        requirement
        for requirement in requirements
        if "==" not in requirement
    ]
    if unpinned:
        raise DeploymentSafetyError(
            "FastAPI requirements must use exact == versions: "
            + ", ".join(unpinned)
        )
