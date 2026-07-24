"""Run the deployment SSH commands independently and report exact results."""

import argparse
import getpass
import importlib.util
import os
import sys
from pathlib import PurePosixPath


def _load_ssh_client():
    """Load ssh.py directly so this probe does not require the FastAPI package."""
    ssh_module_path = os.path.join(os.path.dirname(__file__), "..", "deploy", "ssh.py")
    spec = importlib.util.spec_from_file_location("cicd_ssh_client", ssh_module_path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Cannot load SSH client from {ssh_module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SSHClient


def main() -> int:
    parser = argparse.ArgumentParser(description="Run source-deployment SSH diagnostics.")
    parser.add_argument("--host", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", help="Prefer CICD_SSH_PASSWORD instead.")
    parser.add_argument("--artifact", default="/tmp/EcommerceApp.war")
    parser.add_argument("--deploy-path", default="/var/lib/tomcat9/webapps/")
    parser.add_argument("--service", default="tomcat9")
    args = parser.parse_args()

    password = args.password or os.environ.get("CICD_SSH_PASSWORD")
    if not password:
        password = getpass.getpass("SSH password: ")

    artifact = str(PurePosixPath(args.artifact))
    deploy_path = args.deploy_path.rstrip("/") + "/"
    commands = [
        "whoami",
        "id",
        "pwd",
        "sudo -n whoami",
        "sudo -n /usr/bin/true",
        f"sudo -n cp {artifact} {deploy_path}",
        f"sudo -n systemctl status {args.service}",
    ]

    SSHClient = _load_ssh_client()
    ssh = SSHClient(host=args.host, username=args.user, password=password)
    connected, error = ssh.connect()
    if not connected:
        print(f"CONNECT FAILED: {error}", file=sys.stderr)
        return 2

    try:
        print(f"Connected to {args.user}@{args.host}")
        failures = 0
        for number, command in enumerate(commands, start=1):
            print(f"\n[{number}] command repr: {command!r}")
            print(f"[{number}] command UTF-8 hex: {command.encode('utf-8').hex()}")
            success, stdout, stderr = ssh.execute_command(command)
            print(f"[{number}] success: {success}")
            print(f"[{number}] stdout repr: {stdout!r}")
            print(f"[{number}] stderr repr: {stderr!r}")
            failures += not success
        return 0 if failures == 0 else 1
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
