"""Toast notification system for GP Server Manager.

Floating toast messages that appear at top-right and auto-dismiss.
"""
from __future__ import annotations

import customtkinter as ctk
from typing import Optional
from app.theme import get_colors


class ToastManager:
    """Manages toast notifications for the app.

    Usage:
        toast_mgr = ToastManager(root_window)
        toast_mgr.show("Saved!", type="success")
        toast_mgr.show("Error occurred", type="error")
    """

    MAX_VISIBLE = 3
    AUTO_DISMISS = 3000  # ms
    POSITION_OFFSET = 10  # px from top-right

    def __init__(self, master: ctk.CTk):
        self._master = master
        self._toasts: list[ctk.CTkFrame] = []
        self._counter = 0

    def show(self, message: str, type: str = "info", duration: int = 3000) -> None:
        """Show a toast notification.

        Args:
            message: Toast text.
            type: "success", "warning", "error", or "info".
            duration: Auto-dismiss duration in ms.
        """
        # Remove oldest if at capacity
        while len(self._toasts) >= self.MAX_VISIBLE:
            old = self._toasts.pop(0)
            old.destroy()

        colors = get_colors(ctk.get_appearance_mode())
        bg_map = {
            "success": colors.primary_container,
            "warning": colors.secondary_container,
            "error": colors.error_container,
            "info": colors.surface_container_high,
        }
        icon_map = {
            "success": "✓",
            "warning": "⚠",
            "error": "✗",
            "info": "ℹ",
        }
        text_color_map = {
            "success": colors.on_primary_container,
            "warning": colors.on_secondary_container,
            "error": colors.on_error_container,
            "info": colors.on_surface_variant,
        }

        bg = bg_map.get(type, bg_map["info"])
        icon = icon_map.get(type, icon_map["info"])
        txt = text_color_map.get(type, text_color_map["info"])

        frame = ctk.CTkFrame(
            self._master,
            fg_color=bg,
            corner_radius=8,
            height=36,
        )
        frame.place(
            x=self.POSITION_OFFSET,
            y=self.POSITION_OFFSET + self._counter * 44,
            relwidth=0.3,
            anchor="ne",
        )
        self._counter += 1

        ctk.CTkLabel(
            frame,
            text=f" {icon}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=txt,
        ).pack(side="left", padx=(8, 4))

        ctk.CTkLabel(
            frame,
            text=message,
            font=ctk.CTkFont(size=12),
            text_color=txt,
            wraplength=200,
        ).pack(side="left", fill="y", padx=(0, 8))

        self._toasts.append(frame)

        # Auto-dismiss
        frame.after(duration, lambda: self._dismiss(frame))

    def _dismiss(self, frame: ctk.CTkFrame) -> None:
        if frame in self._toasts:
            self._toasts.remove(frame)
            frame.destroy()
            # Reposition remaining toasts
            self._reposition()

    def _reposition(self) -> None:
        for i, toast in enumerate(self._toasts):
            try:
                toast.place(y=self.POSITION_OFFSET + i * 44)
            except Exception:
                pass
