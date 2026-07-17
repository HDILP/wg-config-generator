"""Launch dialog — mode selection at startup."""
from __future__ import annotations

from typing import Optional, Tuple

import customtkinter as ctk

from app.theme import C, PAD, CR
from app.workspace import WorkspaceMode
from utils.icon_loader import load_icon


class WorkspaceLauncher(ctk.CTkToplevel):
    """Modal dialog shown at app start to pick server/client mode."""

    def __init__(self, parent: ctk.CTk, remember: bool = False):
        super().__init__(parent)
        self.title("GP Server Manager")
        self.geometry("460x420")
        self.configure(fg_color=C["card_bg"])

        self._result: Optional[WorkspaceMode] = None
        self._remember = remember
        self._confirmed = False

        # ── Layout ────────────────────────────────────────────
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="GP Server Manager",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=C["on_surface"],
        ).grid(row=0, column=0, pady=(36, 4))

        ctk.CTkLabel(
            self, text="请选择当前工作模式",
            font=ctk.CTkFont(size=14),
            text_color=C["outline"],
        ).grid(row=1, column=0, pady=(0, 24))

        self._server_var = ctk.StringVar(value="server")
        self._cards: dict[str, ctk.CTkFrame] = {}

        # Server Mode card
        make_card(self, self._server_var, "server", 2,
                  "server", "Server Mode",
                  "在服务器上使用  ·  SQL · WireGuard · 防火墙 · 备份",
                  self._cards)

        # Client Mode card
        make_card(self, self._server_var, "client", 3,
                  "terminal", "Client Mode",
                  "在运维电脑上使用  ·  项目管理 · 客户管理 · 配置生成",
                  self._cards)

        # Highlight initial selection
        self._update_selection()

        # Remember checkbox
        self._remember_var = ctk.BooleanVar(value=remember)
        ctk.CTkCheckBox(
            self, text="记住我的选择", variable=self._remember_var,
            font=ctk.CTkFont(size=13),
            text_color=C["on_surface"],
        ).grid(row=4, column=0, pady=(0, 20))

        # Enter button
        ctk.CTkButton(
            self, text="进入", width=160, height=40,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=C["primary"], text_color=C["on_primary"],
            hover_color=C["primary_hover"], corner_radius=CR,
            command=self._confirm,
        ).grid(row=5, column=0, pady=(0, 24))

        self.grab_set()

    def _confirm(self) -> None:
        self._confirmed = True
        self._result = WorkspaceMode(self._server_var.get())
        self.destroy()

    def _update_selection(self) -> None:
        """Highlight selected card with tint + indicator dot."""
        selected = self._server_var.get()
        for val, card in self._cards.items():
            card.configure(fg_color=C["primary_container"] if val == selected else C["card_bg"])
            # Destroy old indicator
            for w in card.winfo_children():
                if getattr(w, "_indicator", False):
                    w.destroy()
            # Indicator bar at left edge
            if val == selected:
                bar = ctk.CTkFrame(card, width=3, fg_color=C["primary"])
                bar.place(x=0, rely=0, relheight=1)
                bar._indicator = True

    def result(self) -> Tuple[Optional[WorkspaceMode], bool]:
        if not self._confirmed:
            return (None, False)
        return (self._result, self._remember_var.get())


def make_card(parent, var, value, row, icon_name, title, desc, cards):
    """Create a clickable mode selection card."""
    card = ctk.CTkFrame(parent, corner_radius=CR, fg_color=C["card_bg"],
                         border_width=0)
    card.grid(row=row, column=0, padx=40, pady=(0, 8), sticky="ew")
    card.grid_columnconfigure(1, weight=1)
    cards[value] = card

    # Update highlight when selection changes
    var.trace_add("write", lambda *_: parent._update_selection())

    icon = load_icon(icon_name, size=24, color=C["primary"])
    ctk.CTkLabel(card, text="", image=icon).grid(
        row=0, column=0, rowspan=2, padx=(PAD["lg"], 0), pady=14, sticky="w")

    text_frame = ctk.CTkFrame(card, fg_color="transparent")
    text_frame.grid(row=0, column=1, rowspan=2, sticky="w", padx=(PAD["md"], PAD["lg"]))
    text_frame.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(text_frame, text=title,
                 font=ctk.CTkFont(size=15, weight="bold"),
                 text_color=C["on_surface"],
                 anchor="w",
                 ).pack(fill="x")
    ctk.CTkLabel(text_frame, text=desc,
                 font=ctk.CTkFont(size=11),
                 text_color=C["outline"],
                 anchor="w",
                 ).pack(fill="x")

    # Bind click to card + all children so clicking anywhere selects
    cb = lambda e, v=value: var.set(v)
    card.bind("<Button-1>", cb)
    for child in card.winfo_children():
        child.bind("<Button-1>", cb)
        for gc in child.winfo_children():
            gc.bind("<Button-1>", cb)
