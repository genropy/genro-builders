# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""CLI for managing live builder sessions.

Provides run/list/connect/stop commands via the ``genro-live`` console script.

Usage:
    genro-live run myapp.py             # start app
    genro-live run myapp.py --connect   # start app + open REPL in tmux
    genro-live list                     # show running sessions
    genro-live connect myapp            # REPL into running session
    genro-live stop myapp               # stop session
"""
from __future__ import annotations

import argparse
import code
import importlib.util
import os
import readline  # noqa: F401 — enables line editing in REPL
import signal
import shutil
import socket
import subprocess
import sys
from typing import Any

from genro_builders.contrib.live import enable_remote

from genro_builders.contrib.live._proxy import LiveProxy
from genro_builders.contrib.live._registry import LiveRegistry


class LiveCLI:
    """CLI for managing live builder sessions."""

    def __init__(self) -> None:
        self._registry = LiveRegistry()

    def main(self) -> None:
        """Parse arguments and dispatch to the appropriate command."""
        parser = self._build_parser()
        args = parser.parse_args()
        if not hasattr(args, "func"):
            parser.print_help()
            return
        args.func(args)

    def run_app(self, args: argparse.Namespace) -> None:
        """Load module, find Application class, register, run."""
        file_path = args.file
        connect_after = args.connect

        if connect_after and shutil.which("tmux"):
            self._run_with_tmux(file_path, os.path.splitext(os.path.basename(file_path))[0])
            return

        spec = importlib.util.spec_from_file_location("__live_app__", file_path)
        if spec is None or spec.loader is None:
            print(f"Cannot load module from {file_path}", file=sys.stderr)
            sys.exit(1)

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        app_class = None
        for obj in vars(module).values():
            if isinstance(obj, type) and hasattr(obj, "set_builder") and obj.__name__ == "Application":
                app_class = obj
                break

        if app_class is None:
            print("No 'Application' class found in module", file=sys.stderr)
            sys.exit(1)

        port = self._registry.find_free_port()
        app_name = os.path.splitext(os.path.basename(file_path))[0]

        app = app_class()
        server = enable_remote(app, port=port, name=app_name)

        print(f"Live session '{app_name}' on port {server.port}")
        print(f"Token: {server.token}")
        print("Press Ctrl+C to stop")

        try:
            signal.pause()
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            server.stop()
            self._registry.unregister(app_name)

    def list_running(self) -> None:
        """List registered sessions with liveness check."""
        sessions = self._registry.list_all()
        if not sessions:
            print("No live sessions registered")
            return

        dead: list[str] = []
        for name, info in sessions.items():
            port = info["port"]
            alive = self._is_alive(port)
            status = "alive" if alive else "dead"
            print(f"  {name:20s}  port={port:<6d}  [{status}]")
            if not alive:
                dead.append(name)

        for name in dead:
            self._registry.unregister(name)
            print(f"  (cleaned up dead session '{name}')")

    def connect_repl(self, args: argparse.Namespace) -> None:
        """Start an interactive Python REPL connected to a live session."""
        name = args.name
        info = self._registry.get_info(name)
        if info is None:
            print(f"Session '{name}' not found", file=sys.stderr)
            sys.exit(1)

        port = info["port"]
        token = info.get("token", "")

        if not self._is_alive(port):
            print(f"Session '{name}' is not responding on port {port}", file=sys.stderr)
            self._registry.unregister(name)
            sys.exit(1)

        remote = LiveProxy(host="localhost", port=port, token=token)

        builders = remote.builders()
        default_builder = builders[0] if len(builders) == 1 else ""
        source = remote.source(default_builder)
        data = remote.data

        banner = (
            f"Connected to '{name}' (port {port})\n"
            f"Builders: {builders}\n"
            f"Variables: remote, source, data\n"
            f"Slash commands: /help /keys /data /builders /quit\n"
        )
        self._repl_help_text = self._make_help_text(name, port)

        local_vars: dict[str, Any] = {
            "remote": remote,
            "source": source,
            "data": data,
        }

        console = code.InteractiveConsole(locals=local_vars)

        original_runsource = console.runsource

        def patched_runsource(source_code: str, filename: str = "<input>", symbol: str = "single") -> bool:
            stripped = source_code.strip()
            if stripped == "/help":
                print(self._repl_help_text)
                return False
            if stripped == "/keys":
                try:
                    print(remote.source(default_builder).keys())
                except Exception as exc:
                    print(f"Error: {exc}")
                return False
            if stripped == "/data":
                try:
                    print(data.keys())
                except Exception as exc:
                    print(f"Error: {exc}")
                return False
            if stripped == "/builders":
                try:
                    print(remote.builders())
                except Exception as exc:
                    print(f"Error: {exc}")
                return False
            if stripped == "/quit":
                raise SystemExit(0)
            return original_runsource(source_code, filename, symbol)

        console.runsource = patched_runsource  # type: ignore[assignment]
        console.interact(banner=banner, exitmsg="Disconnected")

    def stop_app(self, args: argparse.Namespace) -> None:
        """Send quit command and clean up."""
        name = args.name
        info = self._registry.get_info(name)
        if info is None:
            print(f"Session '{name}' not found", file=sys.stderr)
            sys.exit(1)

        port = info["port"]
        token = info.get("token", "")

        if self._is_alive(port):
            try:
                remote = LiveProxy(host="localhost", port=port, token=token)
                remote.quit()
                print(f"Sent quit to '{name}'")
            except Exception as exc:
                print(f"Error sending quit: {exc}", file=sys.stderr)

        self._registry.unregister(name)

        tmux_session = f"genro-live-{name}"
        if shutil.which("tmux"):
            subprocess.run(
                ["tmux", "kill-session", "-t", tmux_session],
                capture_output=True,
            )

        print(f"Session '{name}' stopped")

    def _is_alive(self, port: int) -> bool:
        """Check if a port is accepting connections on localhost."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.settimeout(1.0)
            sock.connect(("127.0.0.1", port))
            return True
        except (ConnectionRefusedError, OSError):
            return False
        finally:
            sock.close()

    def _run_with_tmux(self, file_path: str, app_name: str) -> None:
        """Run app in tmux: app on top pane, REPL on bottom."""
        session_name = f"genro-live-{app_name}"
        abs_path = os.path.abspath(file_path)

        subprocess.run(
            ["tmux", "kill-session", "-t", session_name],
            capture_output=True,
        )

        subprocess.run([
            "tmux", "new-session", "-d", "-s", session_name,
            "-x", "200", "-y", "50",
            sys.executable, "-m", "genro_builders.contrib.live.cli",
            "run", abs_path,
        ], check=True)

        subprocess.run([
            "tmux", "split-window", "-v", "-t", session_name,
            sys.executable, "-m", "genro_builders.contrib.live.cli",
            "connect", app_name,
        ], check=True)

        subprocess.run(["tmux", "set-option", "-t", session_name, "mouse", "on"], check=True)
        subprocess.run(["tmux", "attach-session", "-t", session_name], check=True)

    def _make_help_text(self, name: str, port: int) -> str:
        """Build REPL help text."""
        return (
            f"\nLive REPL — session '{name}' (port {port})\n"
            f"\n"
            f"Variables:\n"
            f"  remote  — LiveProxy (top-level proxy)\n"
            f"  source  — SourceProxy (default builder source)\n"
            f"  data    — DataProxy (reactive_store)\n"
            f"\n"
            f"Slash commands:\n"
            f"  /help      — show this help\n"
            f"  /keys      — list source keys\n"
            f"  /data      — list data keys\n"
            f"  /builders  — list registered builders\n"
            f"  /quit      — disconnect\n"
            f"\n"
            f"Examples:\n"
            f"  source.div('Hello', _class='main')\n"
            f"  data['title'] = 'New Title'\n"
            f"  remote.source('sidebar').nav('Menu')\n"
        )

    def _build_parser(self) -> argparse.ArgumentParser:
        """Build argparse parser with subcommands."""
        parser = argparse.ArgumentParser(
            prog="genro-live",
            description="Manage live builder sessions",
        )
        subs = parser.add_subparsers()

        run_parser = subs.add_parser("run", help="Start a builder application")
        run_parser.add_argument("file", help="Python file with Application class")
        run_parser.add_argument(
            "--connect", "-c", action="store_true",
            help="Also open REPL (uses tmux if available)",
        )
        run_parser.set_defaults(func=self.run_app)

        list_parser = subs.add_parser("list", help="List running sessions")
        list_parser.set_defaults(func=lambda _: self.list_running())

        connect_parser = subs.add_parser("connect", help="Connect REPL to a session")
        connect_parser.add_argument("name", help="Session name")
        connect_parser.set_defaults(func=self.connect_repl)

        stop_parser = subs.add_parser("stop", help="Stop a session")
        stop_parser.add_argument("name", help="Session name")
        stop_parser.set_defaults(func=self.stop_app)

        comp_parser = subs.add_parser("completions", help="Shell completions")
        comp_parser.add_argument("shell", choices=["zsh", "bash"], default="zsh", nargs="?")
        comp_parser.set_defaults(func=lambda a: self.print_completions(a.shell))

        subs.add_parser("_complete_apps").set_defaults(
            func=lambda _: print("\n".join(self._registry.list_all().keys()))
        )

        return parser

    def print_completions(self, shell: str) -> None:
        """Print shell completion script."""
        if shell == "zsh":
            print(self._generate_zsh_completion())
        else:
            print("# Bash completions not yet implemented")

    def _generate_zsh_completion(self) -> str:
        """Generate zsh completion script."""
        return (
            '#compdef genro-live\n'
            '_genro_live() {\n'
            '    local -a commands\n'
            '    commands=(\n'
            '        "run:Start a builder application"\n'
            '        "list:List running sessions"\n'
            '        "connect:Connect REPL to a session"\n'
            '        "stop:Stop a session"\n'
            '        "completions:Shell completions"\n'
            '    )\n'
            '    if (( CURRENT == 2 )); then\n'
            '        _describe "command" commands\n'
            '    elif (( CURRENT == 3 )); then\n'
            '        case "$words[2]" in\n'
            '            connect|stop)\n'
            '                local -a apps\n'
            '                apps=(${(f)"$(genro-live _complete_apps 2>/dev/null)"})\n'
            '                _describe "app" apps\n'
            '                ;;\n'
            '            run)\n'
            '                _files -g "*.py"\n'
            '                ;;\n'
            '        esac\n'
            '    fi\n'
            '}\n'
            '_genro_live "$@"\n'
        )


def main() -> None:
    """Console script entry point for genro-live."""
    cli = LiveCLI()
    cli.main()


if __name__ == "__main__":
    main()
