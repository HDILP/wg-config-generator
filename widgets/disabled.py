"""Auto-disable context manager for buttons during async operations."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

import customtkinter as ctk


@contextmanager
def AutoDisable(btn: ctk.CTkButton, restore_delay: int = 100) -> Generator[None, None, None]:
    """Temporarily disable a button during an operation.

    Usage:
        with AutoDisable(save_btn):
            save_data()  # runs while button is disabled
        # button restored after context exits
    """
    original_state = btn.cget("state")
    original_fg = btn.cget("fg_color")
    original_text = btn.cget("text")

    btn.configure(state="disabled", text="⏳ ...")
    try:
        yield
    finally:
        def restore() -> None:
            btn.configure(state=original_state, text=original_text)
        btn.after(restore_delay, restore)
