"""Toast notification system for GP Server Manager.

Usage:
    from app.app import GPServerManager  # auto-attached via _init_toast()
    app.show_toast("✓ 已保存", type="success")
    app.show_toast("操作失败", type="error", duration=0)  # persistent
    app.show_modal("确认删除?", on_confirm=cb)  # danger confirmation
"""
from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from app.theme import C, PAD, CR


class ToastFrame(ctk.CTkFrame):
    """A floating toast notification attached to a parent container."""

    _instances: list[ToastFrame] = []

    def __init__(
        self,
        master: ctk.CTk,
        message: str,
        type: str = "success",
        duration: int = 3000,
    ):
        colors = {
            "success": (C["success"], "#E8F5E9"),
            "error": (C["error"], "#FFEBEE"),
            "warning": (C["warning"], "#FFF3E0"),
        }
        fg, bg = colors.get(type, (C["outline"], C["surface_variant"]))

        super().__init__(
            master,
            corner_radius=CR,
            fg_color=bg,
            border_width=0,
        )

        # Icon + text
        icon_map = {"success": "✓", "error": "✗", "warning": "⚠"}
        ctk.CTkLabel(
            self, text=icon_map.get(type, "●"),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=fg,
        ).pack(side="left", padx=(PAD["lg"], PAD["sm"]))
        ctk.CTkLabel(
            self, text=message,
            font=ctk.CTkFont(size=13),
            text_color=C["on_surface"],
        ).pack(side="left", padx=(0, PAD["lg"]), pady=PAD["md"])

        # Stack: move existing toasts up
        offset = sum(f.winfo_height() or 50 for f in ToastFrame._instances)
        ToastFrame._instances.append(self)

        self.place(relx=0.72, rely=0.0, y=16 + offset, anchor="n")
        self.lift()

        if duration > 0:
            self.after(duration, self._dismiss)

    def _dismiss(self) -> None:
        try:
            self.place_forget()
            self.destroy()
        except Exception:
            pass
        finally:
            if self in ToastFrame._instances:
                ToastFrame._instances.remove(self)
            # Reposition remaining toasts
            y = 16
            for t in ToastFrame._instances:
                try:
                    t.place(y=y)
                    y += t.winfo_height() or 50
                except Exception:
                    pass


class ModalConfirm(ctk.CTkToplevel):
    """Custom modal for danger operations (replaces messagebox)."""

    def __init__(
        self,
        parent: ctk.CTk,
        title: str = "确认操作",
        message: str = "确定要执行此操作吗？",
        confirm_text: str = "确认",
        cancel_text: str = "取消",
        on_confirm: Optional[Callable] = None,
        danger: bool = True,
    ):
        super().__init__(parent)
        self.title(title)
        self.geometry("360x180")
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)

        # Center over parent
        px, py = parent.winfo_x(), parent.winfo_y()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        self.geometry(f"+{px + pw // 2 - 180}+{py + ph // 2 - 90}")

        ctk.CTkLabel(
            self, text=message,
            font=ctk.CTkFont(size=13),
            wraplength=320,
        ).pack(pady=(28, 20), padx=20)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 16))

        ctk.CTkButton(
            btn_frame, text=cancel_text, width=90,
            font=ctk.CTkFont(size=13),
            fg_color="transparent",
            text_color=C["on_surface"],
            hover_color=C["surface_variant"],
            command=self.destroy,
        ).pack(side="left", padx=(0, 12))

        btn_fg = C["error"] if danger else C["primary"]
        ctk.CTkButton(
            btn_frame, text=confirm_text, width=100,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=btn_fg,
            text_color="white",
            command=lambda: (self.destroy(), on_confirm() if on_confirm else None),
        ).pack(side="right")

        self._on_confirm = on_confirm
