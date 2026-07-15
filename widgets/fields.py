"""Form field components for GP Server Manager.

FieldRow: a single-row form with label + input + optional helper text.
Uses 8dp spacing rhythm and consistent label alignment.
"""
from __future__ import annotations

import customtkinter as ctk
from typing import Optional


class FieldRow(ctk.CTkFrame):
    """A form row: label (fixed width) + input widget + optional helper."""

    LABEL_WIDTH = 80
    SPACING = 8

    def __init__(
        self,
        master,
        label: str,
        widget: ctk.CTkBaseWidget,
        helper: str = "",
        label_width: int = 0,  # 0 = use default
        **kwargs,
    ):
        w = label_width or self.LABEL_WIDTH
        super().__init__(master, fg_color="transparent", **kwargs)

        self._label = ctk.CTkLabel(
            self,
            text=label,
            width=w,
            anchor="w",
            font=ctk.CTkFont(size=13),
        )
        self._label.pack(side="left", padx=(0, self.SPACING))

        self._widget = widget
        self._widget.pack(side="left", fill="x", expand=True)

        if helper:
            self._helper = ctk.CTkLabel(
                self,
                text=helper,
                font=ctk.CTkFont(size=11),
                text_color="#79747E",
                anchor="w",
            )
            self._helper.pack(side="left", fill="x", expand=True, padx=(self.SPACING, 0))

    @property
    def text_variable(self):
        """Get the textvariable if the widget uses one."""
        return getattr(self._widget, "cget", lambda k: None)("variable")

    def get_value(self) -> str:
        """Get the current value from the input widget."""
        if hasattr(self._widget, "get"):
            return self._widget.get()
        if hasattr(self._widget, "get"):
            try:
                return self._widget.get()
            except Exception:
                return ""
        return ""

    def set_value(self, value: str) -> None:
        """Set the value of the input widget."""
        if hasattr(self._widget, "delete"):
            self._widget.delete(0, "end")
            self._widget.insert(0, value)
        elif hasattr(self._widget, "set"):
            self._widget.set(value)
