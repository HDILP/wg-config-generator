#!/usr/bin/env python3
"""WireGuard Config Generator — entry point."""

from __future__ import annotations

from gui import WireGuardGUI


def main() -> None:
    app = WireGuardGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
