"""CustomTkinter GUI for WireGuard Config Generator."""

from __future__ import annotations

import threading
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Dict, List, Optional

import customtkinter as ctk

from generator import ConfigGenerator, KeyGenError
from keygen import check_wg_available
from models import GenerationConfig
from utils import ensure_dir


class WireGuardGUI(ctk.CTk):
    """Main application window."""

    WIDTH = 520
    HEIGHT = 620

    NEW_SERVER = "New Server"
    ADD_CLIENT = "Add Client"

    def __init__(self) -> None:
        super().__init__()
        self.title("WireGuard Config Generator")
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.resizable(False, False)
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self._wg_error: Optional[str] = check_wg_available()
        if self._wg_error:
            self._build_error_ui()
        else:
            self._build_main_ui()

    # ── error state ──────────────────────────────────────────────

    def _build_error_ui(self) -> None:
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
        ).pack(pady=(12, 4))

        ctk.CTkLabel(
            main,
            text="New server or add client to existing deployment",
            font=ctk.CTkFont(size=12),
            text_color="gray50",
        ).pack(pady=(0, 12))

        # Mode selector
        self._mode_var = ctk.StringVar(value=self.NEW_SERVER)
        mode_sel = ctk.CTkSegmentedButton(
            main,
            values=[self.NEW_SERVER, self.ADD_CLIENT],
            variable=self._mode_var,
            command=self._on_mode_change,
            font=ctk.CTkFont(size=13),
        )
        mode_sel.pack(pady=(0, 12), padx=16, fill="x")

        # Form fields
        fields_frame = ctk.CTkFrame(main, fg_color="transparent")
        fields_frame.pack(fill="x", padx=16)

        self._entries: dict[str, ctk.CTkEntry] = {}
        # (key, label, default, tip, modes_shown) — modes_shown: None = always
        field_defs: list[tuple[str, str, str, str | None, List[str] | None]] = [
            ("server_public_ip", "Server Public IP", "", "公网 IP 或域名", None),
            ("listen_port", "Listen Port", "51820", None, [self.NEW_SERVER]),
            ("server_vpn_ip", "Server VPN IP", "10.66.66.1", None, [self.NEW_SERVER]),
            ("client_vpn_ip", "Client VPN IP", "10.66.66.2", None, None),
            ("vpn_subnet", "VPN Subnet", "10.66.66.0/24", None, [self.NEW_SERVER]),
        ]
        self._field_widgets: dict[str, list[ctk.CTkBaseClass]] = {}
        self._field_modes: dict[str, List[str] | None] = {}

        row = 0
        for key, label, default, tip, modes in field_defs:
            self._field_modes[key] = modes
            lbl = ctk.CTkLabel(
                fields_frame, text=label, font=ctk.CTkFont(size=13),
                anchor="w",
            )
            lbl.grid(row=row, column=0, sticky="w", pady=(8, 2))
            ent = ctk.CTkEntry(
                fields_frame,
                placeholder_text=tip or "",
                font=ctk.CTkFont(size=13),
            )
            ent.insert(0, default)
            ent.grid(row=row + 1, column=0, sticky="ew", pady=(0, 6))
            self._entries[key] = ent
            self._field_widgets[key] = [lbl, ent]
            row += 2

        fields_frame.columnconfigure(0, weight=1)

        # Server config folder (Add Client only)
        self._server_conf_frame = ctk.CTkFrame(fields_frame, fg_color="transparent")
        lbl = ctk.CTkLabel(
            self._server_conf_frame, text="Server Config Folder",
            font=ctk.CTkFont(size=13), anchor="w",
        )
        lbl.pack(fill="x", pady=(8, 2))
        efr = ctk.CTkFrame(self._server_conf_frame, fg_color="transparent")
        efr.pack(fill="x", pady=(0, 6))
        efr.columnconfigure(0, weight=1)
        self._server_conf_entry = ctk.CTkEntry(
            efr, placeholder_text="Folder containing server.conf",
            font=ctk.CTkFont(size=13),
        )
        self._server_conf_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(
            efr, text="Browse", width=80,
            command=self._browse_server_conf,
            font=ctk.CTkFont(size=12),
        ).grid(row=0, column=1)

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
            command=self._browse_output_folder,
            font=ctk.CTkFont(size=12),
        ).grid(row=0, column=1)

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
            text="Keys are auto-generated — no manual editing needed.",
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

        # Start in New Server mode
        self._on_mode_change(self.NEW_SERVER)

    # ── mode switching ───────────────────────────────────────────

    def _on_mode_change(self, mode: str) -> None:
        """Show/hide fields based on mode."""
        is_new = mode == self.NEW_SERVER
        for key, modes in self._field_modes.items():
            visible = modes is None or mode in modes
            for w in self._field_widgets[key]:
                if visible:
                    w.grid()  # reapply remembered grid config
                else:
                    w.grid_remove()
        # Server config folder: shown only in Add Client
        if is_new:
            self._server_conf_frame.grid_remove()
        else:
            self._server_conf_frame.grid(row=0, column=0, sticky="ew")
            # Auto-fill output from server folder if entered
            self._sync_output_from_server_conf()

    def _sync_output_from_server_conf(self) -> None:
        path = self._server_conf_entry.get().strip()
        if path and not self._output_entry.get().strip():
            self._output_entry.delete(0, "end")
            self._output_entry.insert(0, path)

    # ── browse handlers ──────────────────────────────────────────

    def _browse_server_conf(self) -> None:
        path = filedialog.askdirectory(title="Select Server Config Folder")
        if path:
            self._server_conf_entry.delete(0, "end")
            self._server_conf_entry.insert(0, path)
            if not self._output_entry.get().strip():
                self._output_entry.delete(0, "end")
                self._output_entry.insert(0, path)

    def _browse_output_folder(self) -> None:
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

        mode = self._mode_var.get()

        if mode == self.NEW_SERVER:
            ip = self._entries["server_public_ip"].get().strip()
            if not ip:
                messagebox.showwarning("Missing Field", "Server Public IP is required.")
                return
        else:
            svr = self._server_conf_entry.get().strip()
            if not svr or not (Path(svr) / "server.conf").exists():
                messagebox.showwarning(
                    "Missing Field",
                    "Select a folder containing server.conf.",
                )
                return

        self._gen_btn.configure(state="disabled", text="Generating…")
        self._status_var.set("Working…")
        self._status_label.configure(text_color="gray40")
        threading.Thread(target=self._generate_worker, daemon=True).start()

    def _generate_worker(self) -> None:
        try:
            mode = self._mode_var.get()
            if mode == self.NEW_SERVER:
                result = self._do_new_server()
            else:
                result = self._do_add_client()
            self.after(0, self._on_success, result)
        except KeyGenError as exc:
            self.after(0, self._on_error, str(exc))
        except Exception as exc:  # noqa: BLE001
            self.after(0, self._on_error, f"Unexpected error: {exc}")

    def _do_new_server(self) -> Dict[str, str]:
        cfg = self._get_config()
        gen = ConfigGenerator(cfg)
        if self._open_folder_var.get():
            return gen.generate_with_open()
        return gen.generate()

    def _do_add_client(self) -> Dict[str, str]:
        server_dir = self._server_conf_entry.get().strip()
        pub_ip = self._entries["server_public_ip"].get().strip()
        client_ip = self._entries["client_vpn_ip"].get().strip()
        output = self._output_entry.get().strip() or server_dir
        subnet = self._entries["vpn_subnet"].get().strip() or "10.66.66.0/24"

        cfg = GenerationConfig(
            server_public_ip=pub_ip,
            output_dir=output,
            vpn_subnet=subnet,
        )
        gen = ConfigGenerator(cfg)
        result = gen.add_client(
            server_conf_dir=server_dir,
            server_public_ip=pub_ip,
            client_vpn_ip=client_ip or None,
            vpn_subnet=subnet,
        )
        if self._open_folder_var.get():
            open_folder(ensure_dir(result["output_dir"]))
        return result

    # ── result display ───────────────────────────────────────────

    def _on_success(self, result: Dict[str, str]) -> None:
        self._gen_btn.configure(state="normal", text="Generate")
        mode = self._mode_var.get()
        self._status_var.set("Done ✓")
        self._status_label.configure(text_color="green")
        msg = (
            f"Output: {result['output_dir']}\n\n"
            f"Server PublicKey:\n{result['server_pubkey']}\n\n"
            f"Client PublicKey:\n{result['client_pubkey']}"
        )
        if mode == self.ADD_CLIENT:
            msg = f"Client appended to existing server.conf\n\n" + msg
        messagebox.showinfo("Success", msg)

    def _on_error(self, msg: str) -> None:
        self._gen_btn.configure(state="normal", text="Generate")
        self._status_var.set("Error — see details")
        self._status_label.configure(text_color="red")
        messagebox.showerror("Generation Failed", msg)
