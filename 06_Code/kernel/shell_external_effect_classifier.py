"""
shell_external_effect_classifier.py
=====================================
Classifies shell commands as "external-effect" or "local/safe".

External-effect commands interact with external networks, services,
or systems outside the local workspace boundary.  These require
Founder approval before execution.

Local/safe commands operate only within the workspace boundaries
(read-only, test, build, file inspection, etc.) and do not require
additional approval beyond existing ExecutionAuthorization.

Used by ToolDispatcher._enforce_shell_run_policy to implement the
``approval_required_for_external_effects`` policy declared in the
ToolRegistry.
"""

from __future__ import annotations

import os
import shlex
from typing import Any, Dict, List, Union


# Commands that ALWAYS have external effects regardless of subcommand.
_ALWAYS_EXTERNAL: frozenset[str] = frozenset(
    {
        # Network transfer / download
        "curl",
        "wget",
        "nc",
        "netcat",
        "ncat",
        "telnet",
        # Remote shell / copy
        "ssh",
        "scp",
        "sftp",
        "ftp",
        "tftp",
        "rsync",
        # Mail / messaging
        "mail",
        "sendmail",
        "mutt",
        # Cloud / deploy CLIs
        "railway",
        "heroku",
        "vercel",
        "netlify",
        "flyctl",
        # Publishing tools
        "twine",
        # Cloud provider CLIs
        "gcloud",
        "aws",
        "az",
        # GitHub CLI — all subcommands involve network
        "gh",
    }
)

# Commands that are external only for specific subcommands.
# Key: base command name; Value: frozenset of external subcommands.
_CONDITIONAL_EXTERNAL: dict[str, frozenset[str]] = {
    "git": frozenset({"push", "pull", "fetch", "clone", "remote"}),
    "docker": frozenset({"push", "pull", "login", "logout"}),
    "npm": frozenset({"publish"}),
    "yarn": frozenset({"publish"}),
    "pip": frozenset({"upload"}),
    "pip3": frozenset({"upload"}),
    "apt": frozenset({"install", "update", "upgrade", "dist-upgrade"}),
    "apt-get": frozenset({"install", "update", "upgrade", "dist-upgrade"}),
    "yum": frozenset({"install", "update"}),
    "brew": frozenset({"install", "upgrade", "update"}),
    "snap": frozenset({"install", "refresh"}),
}


def _parse_argv(command: Union[str, List[Any]]) -> List[str]:
    """Parse a command string or list into an argv list."""
    if isinstance(command, list):
        return [str(c) for c in command if c is not None and str(c).strip()]
    if isinstance(command, str) and command.strip():
        try:
            return shlex.split(command)
        except ValueError:
            return command.split()
    return []


def _command_root(argv: List[str]) -> str:
    """Return the lowercased base name of the first argv element (strips path prefix)."""
    if not argv:
        return ""
    return os.path.basename(argv[0]).lower().strip()


class ShellExternalEffectClassifier:
    """
    Classifies shell commands as external-effect or local/safe.

    Usage:
        result = ShellExternalEffectClassifier.classify("curl https://example.com")
        result["is_external_effect"]  # True
        result["command_root"]        # "curl"
        result["reason"]              # "curl always has external effects"

        ShellExternalEffectClassifier.is_external_effect(["git", "push"])  # True
        ShellExternalEffectClassifier.is_external_effect(["git", "status"])  # False
        ShellExternalEffectClassifier.is_external_effect("echo hello")  # False
    """

    @classmethod
    def classify(cls, command: Union[str, List[Any]]) -> Dict[str, Any]:
        """
        Classify a shell command.

        Returns a dict:
            is_external_effect : bool  — True if command has external effects
            command_root       : str   — base command name (e.g. "curl")
            subcommand         : str   — first subcommand if applicable (e.g. "push")
            reason             : str   — human-readable classification reason
        """
        argv = _parse_argv(command)
        if not argv:
            return {
                "is_external_effect": False,
                "command_root": "",
                "subcommand": "",
                "reason": "empty_command",
            }

        root = _command_root(argv)
        subcommand = argv[1].lower().strip() if len(argv) > 1 else ""

        if root in _ALWAYS_EXTERNAL:
            return {
                "is_external_effect": True,
                "command_root": root,
                "subcommand": subcommand,
                "reason": f"{root!r} always has external effects",
            }

        if root in _CONDITIONAL_EXTERNAL:
            if subcommand in _CONDITIONAL_EXTERNAL[root]:
                return {
                    "is_external_effect": True,
                    "command_root": root,
                    "subcommand": subcommand,
                    "reason": f"{root!r} {subcommand!r} has external effects",
                }
            return {
                "is_external_effect": False,
                "command_root": root,
                "subcommand": subcommand,
                "reason": f"{root!r} {subcommand!r} is local/read-only",
            }

        return {
            "is_external_effect": False,
            "command_root": root,
            "subcommand": subcommand,
            "reason": "local_or_safe_command",
        }

    @classmethod
    def is_external_effect(cls, command: Union[str, List[Any]]) -> bool:
        """Return True if the command has external effects."""
        return cls.classify(command)["is_external_effect"]
