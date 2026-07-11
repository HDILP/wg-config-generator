"""CustomTkinter GUI for WireGuard Config Generator."""

from __future__ import annotations

import threading
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional

import customtkinter as ctk

from generator import ConfigGenerator, KeyGenError
from keygen import check_wg_available
from models import GenerationConfig
from utils import ensure_dir


class WireGuardGUI(ctk.CTk):
    """Main application window."""

    WIDTH = 520
    HEIGHT = 580

    def __init__(self) -> None:
        super().__init__()
        self.title("WireGuard Config Generator")
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.resizable(False, False)
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        # Validate wg availability early
        self._wg_error: Optional[str] = check_wg_available()
        if self._wg_error:
            self._build_error_ui()
        else:
            self._build_main_ui()

    # ── error state ──────────────────────────────────────────────

    def _build_error_ui(self) -> None:
        """Show a message when wg is not found."""
        frame = ctk.CTkFrame(self, corner_radius=12)
        frame.pack(expand=True, fill="both", padx=30, pady=30)

        ctk.CTkLabel(
            frame,
            text="⚠️  WireGuard Not Found",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=(30, 10))

        ctk.CTkLabel(
            frame,
            text=self._wg_error or "",
            wraplength=400,
            font=ctk.CTkFont(size=13),
            text_color="gray40",
        ).pack(pady=10)

        ctk.CTkLabel(
            frame,
            text="Please install WireGuard and ensure `wg` is on your PATH,\nthen restart this application.",
            wraplength=400,
            font=ctk.CTkFont(size=12),
            text_color="gray50",
        ).pack(pady=(5, 30))

    # ── main form ────────────────────────────────────────────────

    def _build_main_ui(self) -> None:
        main = ctk.CTkFrame(self, corner_radius=12)
        main.pack(expand=True, fill="both", padx=20, pady=20)

        # Title
        ctk.CTkLabel(
            main,
            text="WireGuard Config Generator",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(pady=(12, 8))

        ctk.CTkLabel(
            main,
            text="Generate server.conf + client.conf in one click",
            font=ctk.CTkFont(size=12),
            text_color="gray50",
        ).pack(pady=(0, 16))

        # Form fields
        fields_frame = ctk.CTkFrame(main, fg_color="transparent")
        fields_frame.pack(fill="x", padx=16)

        self._entries: dict[str, ctk.CTkEntry] = {}

        row = 0
        for label, key, default, tip in [
            ("Server Public IP", "server_public_ip", "", "公网 IP 或域名"),
            ("Listen Port", "listen_port", "51820", None),
            ("Server VPN IP", "server_vpn_ip", "10.66.66.1", None),
            ("Client VPN IP", "client_vpn_ip", "10.66.66.2", None),
            ("VPN Subnet", "vpn_subnet", "10.66.66.0/24", None),
        ]:
            ctk.CTkLabel(
                fields_frame, text=label, font=ctk.CTkFont(size=13),
                anchor="w",
            ).grid(row=row, column=0, sticky="w", pady=(8, 2))

            entry = ctk.CTkEntry(
                fields_frame,
                placeholder_text=tip or "",
                font=ctk.CTkFont(size=13),
            )
            entry.insert(0, default)
            entry.grid(row=row + 1, column=0, sticky="ew", pady=(0, 6))
            self._entries[key] = entry
            row += 2

        # Output folder row
        ctk.CTkLabel(
            fields_frame, text="Output Folder", font=ctk.CTkFont(size=13),
            anchor="w",
        ).grid(row=row, column=0, sticky="w", pady=(8, 2))

        folder_frame = ctk.CTkFrame(fields_frame, fg_color="transparent")
        folder_frame.grid(row=row + 1, column=0, sticky="ew", pady=(0, 6))
        folder_frame.columnconfigure(0, weight=1)

        self._output_entry = ctk.CTkEntry(
            folder_frame, placeholder_text="output/",
            font=ctk.CTkFont(size=13),
        )
        self._output_entry.insert(0, "output")
        self._output_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        ctk.CTkButton(
            folder_frame, text="Browse", width=80,
            command=self._browse_folder,
            font=ctk.CTkFont(size=12),
        ).grid(row=0, column=1)

        fields_frame.columnconfigure(0, weight=1)

        # Options
        opts_frame = ctk.CTkFrame(main, fg_color="transparent")
        opts_frame.pack(fill="x", padx=16, pady=(8, 4))

        self._open_folder_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            opts_frame, text="Open output folder after generation",
            variable=self._open_folder_var,
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w")

        ctk.CTkLabel(
            opts_frame,
            text="Keys are auto-generated by wg.exe — no manual editing needed.",
            font=ctk.CTkFont(size=11),
            text_color="gray50",
        ).pack(anchor="w", pady=(2, 0))

        # Generate button
        self._gen_btn = ctk.CTkButton(
            main,
            text="Generate",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=42,
            corner_radius=8,
            command=self._on_generate,
        )
        self._gen_btn.pack(pady=(12, 16), padx=40, fill="x")

        # Status bar
        self._status_var = ctk.StringVar(value="Ready")
        self._status_label = ctk.CTkLabel(
            main,
            textvariable=self._status_var,
            font=ctk.CTkFont(size=11),
            text_color="gray40",
        )
        self._status_label.pack(pady=(0, 8))

    # ── helpers ──────────────────────────────────────────────────

    def _browse_folder(self) -> None:
        path = filedialog.askdirectory(title="Select Output Folder")
        if path:
            self._output_entry.delete(0, "end")
            self._output_entry.insert(0, path)

    def _get_config(self) -> GenerationConfig:
        val = self._entries
        return GenerationConfig(
            server_public_ip=val["server_public_ip"].get().strip(),
            listen_port=int(val["listen_port"].get().strip() or "51820"),
            server_vpn_ip=val["server_vpn_ip"].get().strip() or "10.66.66.1",
            client_vpn_ip=val["client_vpn_ip"].get().strip() or "10.66.66.2",
            vpn_subnet=val["vpn_subnet"].get().strip() or "10.66.66.0/24",
            output_dir=self._output_entry.get().strip() or "output",
        )

    # ── generation ───────────────────────────────────────────────

    def _on_generate(self) -> None:
        if self._wg_error:
            messagebox.showerror("Error", self._wg_error)
            return

        ip = self._entries["server_public_ip"].get().strip()
        if not ip:
            messagebox.showwarning("Missing Field", "Server Public IP is required.")
            return

        self._gen_btn.configure(state="disabled", text="Generating…")
        self._status_var.set("Generating keys and configs…")
        self._status_label.configure(text_color="gray40")
        # Run in background so UI stays responsive
        threading.Thread(target=self._generate_worker, daemon=True).start()

    def _generate_worker(self) -> None:
        try:
            cfg = self._get_config()
            gen = ConfigGenerator(cfg)
            if self._open_folder_var.get():
                result = gen.generate_with_open()
            else:
                result = gen.generate()

            self.after(0, self._on_success, result)
        except KeyGenError as exc:
            self.after(0, self._on_error, str(exc))
        except Exception as exc:  # noqa: BLE001
            self.after(0, self._on_error, f"Unexpected error: {exc}")

    def _on_success(self, result: dict[str, str]) -> None:
        self._gen_btn.configure(state="normal", text="Generate")
        self._status_var.set("Done ✓  Configs written to output folder")
        self._status_label.configure(text_color="green")
        messagebox.showinfo(
            "Success",
            f"Configs generated successfully!\n\n"
            f"Output: {result['output_dir']}\n\n"
            f"Server PublicKey:\n{result['server_pubkey']}\n\n"
            f"Client PublicKey:\n{result['client_pubkey']}",
        )

    def _on_error(self, msg: str) -> None:
        self._gen_btn.configure(state="normal", text="Generate")
        self._status_var.set("Error — see details")
        self._status_label.configure(text_color="red")
        messagebox.showerror("Generation Failed", msg)
