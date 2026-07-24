"""Deployment strategies with an explicit, tested Linux contract."""

import os
import posixpath
import shlex
from typing import Callable, Optional

from backend.deploy.artifacts import (
    DeploymentSafetyError,
    RemoteRelease,
    install_user_service,
    resolve_artifact_path,
    restart_user_service,
    run_checked,
    transfer_artifact,
    validate_express_artifact,
    validate_fastapi_artifact,
    validate_identifier,
    validate_remote_deploy_path,
    wait_for_http_health,
    wait_for_user_service_health,
)

from .base import DeploymentContext, DeploymentStrategy, StrategyTier


def _health_port(context: DeploymentContext, default: int) -> int:
    return context.health_check_port or default


def _release_id(context: DeploymentContext) -> str:
    return context.release_id or "manual"


def _remember_release(
    context: DeploymentContext,
    release: RemoteRelease,
    restart: Callable[[], None],
    stop: Optional[Callable[[], None]] = None,
) -> None:
    context.additional_params["_release"] = release
    context.additional_params["_restart_release"] = restart
    context.additional_params["_stop_release"] = stop


def _rollback(
    context: DeploymentContext,
    log_func,
) -> None:
    release = context.additional_params.get("_release")
    if not isinstance(release, RemoteRelease):
        return

    log_func("Rolling back to the previous release...")
    release.rollback(context.ssh_client)
    if release.previous_target:
        restart = context.additional_params.get("_restart_release")
        if restart:
            restart()
    else:
        stop = context.additional_params.get("_stop_release")
        if stop:
            stop()
    log_func("Rollback completed")


def _discard_unactivated(
    ssh_client,
    release: Optional[RemoteRelease],
    log_func,
) -> None:
    if release is None:
        return
    try:
        release.discard(ssh_client)
    except DeploymentSafetyError as cleanup_error:
        log_func(f"Failed to discard incomplete release: {cleanup_error}")


def _service_stop_command(service_name: str) -> str:
    service_name = validate_identifier(service_name, "Service name")
    return (
        f"systemctl --user stop {shlex.quote(service_name)}.service "
        "2>/dev/null || true"
    )


class VerifiedExpressStrategy(DeploymentStrategy):
    @property
    def name(self) -> str:
        return "Express"

    @property
    def supported_frameworks(self) -> list[str]:
        return ["Express"]

    @property
    def supported_runtimes(self) -> list[str]:
        return ["Node.js"]

    @property
    def tier(self) -> StrategyTier:
        return StrategyTier.VERIFIED

    @property
    def supported_artifact_types(self) -> list[str]:
        return ["directory"]

    @property
    def required_tools(self) -> list[str]:
        return ["node", "npm", "curl", "systemd --user"]

    @property
    def default_health_check_port(self) -> int:
        return 3000

    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework == "Express" and runtime == "Node.js"

    def execute(self, context: DeploymentContext, log_func) -> bool:
        release = None
        activated = False
        try:
            artifact = resolve_artifact_path(
                context.artifact_path or "",
                context.workspace_dir,
            )
            if not os.path.isdir(artifact):
                raise DeploymentSafetyError(
                    "Express verified profile requires a directory artifact"
                )
            validate_express_artifact(artifact)
            deploy_path = validate_remote_deploy_path(context.deploy_path)
            service_name = validate_identifier(
                context.service_name,
                "Service name",
            )
            port = _health_port(context, self.default_health_check_port)

            release = RemoteRelease.prepare(
                context.ssh_client,
                deploy_path,
                _release_id(context),
            )
            transfer_artifact(
                context.ssh_client,
                artifact,
                "directory",
                release.release_path,
                log_func,
                workspace_dir=context.workspace_dir,
            )
            run_checked(
                context.ssh_client,
                (
                    f"cd {shlex.quote(release.release_path)} && "
                    "npm ci --omit=dev"
                ),
                "npm ci failed",
            )
            release.activate(context.ssh_client)
            activated = True

            unit = (
                "[Unit]\n"
                "Description=Mini-CICD Express application\n"
                "After=network.target\n\n"
                "[Service]\n"
                "Type=simple\n"
                f"WorkingDirectory={release.current_path}\n"
                "Environment=NODE_ENV=production\n"
                f"Environment=PORT={port}\n"
                "ExecStart=/usr/bin/npm start\n"
                "Restart=on-failure\n"
                "RestartSec=3\n\n"
                "[Install]\n"
                "WantedBy=default.target\n"
            )
            install_user_service(context.ssh_client, service_name, unit)
            restart = lambda: restart_user_service(
                context.ssh_client,
                service_name,
            )
            stop = lambda: context.ssh_client.execute_command(
                _service_stop_command(service_name)
            )
            _remember_release(context, release, restart, stop)
            restart()
            return True
        except Exception as error:
            log_func(f"Express deployment failed: {error}")
            if activated:
                try:
                    _rollback(context, log_func)
                except Exception as rollback_error:
                    log_func(f"Rollback failed: {rollback_error}")
            else:
                _discard_unactivated(context.ssh_client, release, log_func)
            return False

    def validate(self, context: DeploymentContext, log_func) -> bool:
        port = _health_port(context, self.default_health_check_port)
        valid = wait_for_user_service_health(
            context.ssh_client,
            context.service_name,
            port,
            context.health_check_path,
        )
        if valid:
            context.additional_params["_release"].prune(context.ssh_client)
            return True
        log_func("Express service or HTTP health check failed")
        _rollback(context, log_func)
        return False

    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/var/www/{project_name.lower()}"


class VerifiedFastAPIStrategy(DeploymentStrategy):
    @property
    def name(self) -> str:
        return "FastAPI"

    @property
    def supported_frameworks(self) -> list[str]:
        return ["FastAPI"]

    @property
    def supported_runtimes(self) -> list[str]:
        return ["Python"]

    @property
    def tier(self) -> StrategyTier:
        return StrategyTier.VERIFIED

    @property
    def supported_artifact_types(self) -> list[str]:
        return ["directory"]

    @property
    def required_tools(self) -> list[str]:
        return ["python3", "python3-venv", "curl", "systemd --user"]

    @property
    def default_health_check_port(self) -> int:
        return 8000

    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework == "FastAPI" and runtime == "Python"

    def execute(self, context: DeploymentContext, log_func) -> bool:
        release = None
        activated = False
        try:
            artifact = resolve_artifact_path(
                context.artifact_path or "",
                context.workspace_dir,
            )
            if not os.path.isdir(artifact):
                raise DeploymentSafetyError(
                    "FastAPI verified profile requires a directory artifact"
                )
            validate_fastapi_artifact(artifact)
            deploy_path = validate_remote_deploy_path(context.deploy_path)
            service_name = validate_identifier(
                context.service_name,
                "Service name",
            )
            port = _health_port(context, self.default_health_check_port)

            release = RemoteRelease.prepare(
                context.ssh_client,
                deploy_path,
                _release_id(context),
            )
            transfer_artifact(
                context.ssh_client,
                artifact,
                "directory",
                release.release_path,
                log_func,
                workspace_dir=context.workspace_dir,
            )
            venv_path = posixpath.join(release.release_path, ".venv")
            requirements_path = posixpath.join(
                release.release_path,
                "requirements.txt",
            )
            run_checked(
                context.ssh_client,
                (
                    f"python3 -m venv {shlex.quote(venv_path)} && "
                    f"{shlex.quote(posixpath.join(venv_path, 'bin/pip'))} "
                    "install --disable-pip-version-check --no-input "
                    f"--requirement {shlex.quote(requirements_path)}"
                ),
                "FastAPI dependency installation failed",
            )
            release.activate(context.ssh_client)
            activated = True

            unit = (
                "[Unit]\n"
                "Description=Mini-CICD FastAPI application\n"
                "After=network.target\n\n"
                "[Service]\n"
                "Type=simple\n"
                f"WorkingDirectory={release.current_path}\n"
                f"ExecStart={release.current_path}/.venv/bin/uvicorn "
                f"main:app --host 127.0.0.1 --port {port}\n"
                "Restart=on-failure\n"
                "RestartSec=3\n\n"
                "[Install]\n"
                "WantedBy=default.target\n"
            )
            install_user_service(context.ssh_client, service_name, unit)
            restart = lambda: restart_user_service(
                context.ssh_client,
                service_name,
            )
            stop = lambda: context.ssh_client.execute_command(
                _service_stop_command(service_name)
            )
            _remember_release(context, release, restart, stop)
            restart()
            return True
        except Exception as error:
            log_func(f"FastAPI deployment failed: {error}")
            if activated:
                try:
                    _rollback(context, log_func)
                except Exception as rollback_error:
                    log_func(f"Rollback failed: {rollback_error}")
            else:
                _discard_unactivated(context.ssh_client, release, log_func)
            return False

    def validate(self, context: DeploymentContext, log_func) -> bool:
        port = _health_port(context, self.default_health_check_port)
        valid = wait_for_user_service_health(
            context.ssh_client,
            context.service_name,
            port,
            context.health_check_path,
        )
        if valid:
            context.additional_params["_release"].prune(context.ssh_client)
            return True
        log_func("FastAPI service or HTTP health check failed")
        _rollback(context, log_func)
        return False

    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/opt/mini-cicd-apps/{project_name.lower()}"


class VerifiedSpringBootJarStrategy(DeploymentStrategy):
    @property
    def name(self) -> str:
        return "Spring Boot JAR"

    @property
    def supported_frameworks(self) -> list[str]:
        return ["Spring Boot"]

    @property
    def supported_runtimes(self) -> list[str]:
        return ["Java"]

    @property
    def tier(self) -> StrategyTier:
        return StrategyTier.VERIFIED

    @property
    def supported_artifact_types(self) -> list[str]:
        return ["jar", "file"]

    @property
    def required_tools(self) -> list[str]:
        return ["java", "curl", "systemd --user"]

    @property
    def default_health_check_port(self) -> int:
        return 8080

    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework == "Spring Boot" and runtime == "Java"

    def execute(self, context: DeploymentContext, log_func) -> bool:
        release = None
        activated = False
        try:
            artifact = resolve_artifact_path(
                context.artifact_path or "",
                context.workspace_dir,
            )
            if not os.path.isfile(artifact) or not artifact.endswith(".jar"):
                raise DeploymentSafetyError(
                    "Spring Boot verified profile requires one JAR artifact"
                )
            deploy_path = validate_remote_deploy_path(context.deploy_path)
            service_name = validate_identifier(
                context.service_name,
                "Service name",
            )
            port = _health_port(context, self.default_health_check_port)

            release = RemoteRelease.prepare(
                context.ssh_client,
                deploy_path,
                _release_id(context),
            )
            remote_jar = transfer_artifact(
                context.ssh_client,
                artifact,
                "jar",
                release.release_path,
                log_func,
                workspace_dir=context.workspace_dir,
            )
            release.activate(context.ssh_client)
            activated = True
            current_jar = posixpath.join(
                release.current_path,
                posixpath.basename(remote_jar),
            )

            unit = (
                "[Unit]\n"
                "Description=Mini-CICD Spring Boot application\n"
                "After=network.target\n\n"
                "[Service]\n"
                "Type=simple\n"
                f"WorkingDirectory={release.current_path}\n"
                f"ExecStart=/usr/bin/java -jar {current_jar} "
                "--server.address=127.0.0.1 "
                f"--server.port={port}\n"
                "Restart=on-failure\n"
                "RestartSec=3\n\n"
                "[Install]\n"
                "WantedBy=default.target\n"
            )
            install_user_service(context.ssh_client, service_name, unit)
            restart = lambda: restart_user_service(
                context.ssh_client,
                service_name,
            )
            stop = lambda: context.ssh_client.execute_command(
                _service_stop_command(service_name)
            )
            _remember_release(context, release, restart, stop)
            restart()
            return True
        except Exception as error:
            log_func(f"Spring Boot deployment failed: {error}")
            if activated:
                try:
                    _rollback(context, log_func)
                except Exception as rollback_error:
                    log_func(f"Rollback failed: {rollback_error}")
            else:
                _discard_unactivated(context.ssh_client, release, log_func)
            return False

    def validate(self, context: DeploymentContext, log_func) -> bool:
        port = _health_port(context, self.default_health_check_port)
        valid = wait_for_user_service_health(
            context.ssh_client,
            context.service_name,
            port,
            context.health_check_path,
        )
        if valid:
            context.additional_params["_release"].prune(context.ssh_client)
            return True
        log_func("Spring Boot service or HTTP health check failed")
        _rollback(context, log_func)
        return False

    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/opt/mini-cicd-apps/{project_name.lower()}"


class VerifiedReactStaticStrategy(DeploymentStrategy):
    @property
    def name(self) -> str:
        return "React/Vite Static"

    @property
    def supported_frameworks(self) -> list[str]:
        return ["React"]

    @property
    def supported_runtimes(self) -> list[str]:
        return ["Node.js"]

    @property
    def tier(self) -> StrategyTier:
        return StrategyTier.VERIFIED

    @property
    def supported_artifact_types(self) -> list[str]:
        return ["directory"]

    @property
    def required_tools(self) -> list[str]:
        return ["nginx", "curl"]

    @property
    def default_health_check_port(self) -> int:
        return 80

    def can_handle(self, framework: str, runtime: str) -> bool:
        return framework == "React" and runtime == "Node.js"

    def execute(self, context: DeploymentContext, log_func) -> bool:
        release = None
        activated = False
        try:
            artifact = resolve_artifact_path(
                context.artifact_path or "",
                context.workspace_dir,
            )
            if not os.path.isdir(artifact):
                raise DeploymentSafetyError(
                    "React/Vite verified profile requires a directory artifact"
                )
            if not os.path.isfile(os.path.join(artifact, "index.html")):
                raise DeploymentSafetyError(
                    "React/Vite artifact requires dist/index.html"
                )
            deploy_path = validate_remote_deploy_path(context.deploy_path)
            release = RemoteRelease.prepare(
                context.ssh_client,
                deploy_path,
                _release_id(context),
            )
            transfer_artifact(
                context.ssh_client,
                artifact,
                "directory",
                release.release_path,
                log_func,
                workspace_dir=context.workspace_dir,
            )
            release.activate(context.ssh_client)
            activated = True

            restart = lambda: run_checked(
                context.ssh_client,
                "sudo -n systemctl reload nginx",
                "Failed to reload nginx",
            )
            _remember_release(context, release, restart)
            restart()
            return True
        except Exception as error:
            log_func(f"React/Vite static deployment failed: {error}")
            if activated:
                try:
                    _rollback(context, log_func)
                except Exception as rollback_error:
                    log_func(f"Rollback failed: {rollback_error}")
            else:
                _discard_unactivated(context.ssh_client, release, log_func)
            return False

    def validate(self, context: DeploymentContext, log_func) -> bool:
        release = context.additional_params["_release"]
        index_path = posixpath.join(release.current_path, "index.html")
        index_success, _, _ = context.ssh_client.execute_command(
            f"test -f {shlex.quote(index_path)}"
        )
        nginx_success, nginx_stdout, _ = (
            context.ssh_client.execute_command(
                "systemctl is-active nginx"
            )
        )
        port = _health_port(context, self.default_health_check_port)
        valid = (
            index_success
            and nginx_success
            and nginx_stdout.strip() == "active"
            and wait_for_http_health(
                context.ssh_client,
                port,
                context.health_check_path,
            )
        )
        if valid:
            release.prune(context.ssh_client)
            return True
        log_func("React/Vite static validation failed")
        _rollback(context, log_func)
        return False

    def get_default_deploy_path(self, project_name: str) -> str:
        return f"/var/www/{project_name.lower()}"

    def get_default_service_name(self, project_name: str) -> str:
        return "nginx"
