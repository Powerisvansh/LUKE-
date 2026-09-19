#!/usr/bin/env python3
"""LukeShell client: tell a running shell to focus home / open the launcher
or the quick-settings sheet. Starts the shell if it is not running."""

import os
import socket
import subprocess
import sys
import time

FW = os.path.expanduser("~/.luke/framework")
if os.path.isdir(FW):
    sys.path.insert(0, FW)
else:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "framework"))

from lukepaths import p, ROOT  # noqa: E402

SOCK = p("state", "lukeshell.sock")
MODES = ("home", "launcher", "quick")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in MODES else "home"
    try:
        os.makedirs(os.path.dirname(SOCK), exist_ok=True)
    except OSError:
        pass
    for _ in range(12):
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect(SOCK)
            s.sendall(mode.encode())
            s.close()
            sys.exit(0)
        except OSError:
            time.sleep(0.15)
    subprocess.Popen(
        ["python3", os.path.join(ROOT, "shell", "main.py"), mode],
        start_new_session=True)


if __name__ == "__main__":
    main()