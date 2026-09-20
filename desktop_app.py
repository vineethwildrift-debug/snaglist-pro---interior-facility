import csv
import os
import sys
import tkinter as tk
import zipfile
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from openpyxl import Workbook

from snaglist_pro.parse_export import parse_whatsapp_text


WINDOW_TITLE = "Snaglist Pro"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"


def _safe_font(size, weight="normal"):
    family = "Segoe UI"
    if weight and weight.lower() == "bold":
        return (family, size, "bold")
    return (family, size)


class SnaglistDesktopApp:
    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry("920x620")
        self.root.minsize(820, 540)
        self.root.configure(bg="#0f172a")
        self.root.option_add("*Font", "{Segoe UI} 10")

        self.current_user = None
        self.selected_zip = None
        self.selected_checklist = None
        self.latest_output_file = None
        self.download_btn = None
        self.status_var = tk.StringVar(value="Idle")
        self.progress_var = tk.DoubleVar(value=0)
        self.stat_vars = {}
        self._apply_modern_theme()
        self._build_login_screen()

    def _apply_modern_theme(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure("Modern.TFrame", background="#f8fafc")
        style.configure("Modern.TLabel", background="#f8fafc", foreground="#0f172a")
        style.configure("ModernAccent.TLabel", background="#0f172a", foreground="#f8fafc")
        style.configure("Modern.TButton", padding=(16, 10), relief="flat", background="#2563eb", foreground="#ffffff", font=_safe_font(10, "bold"))
        style.map("Modern.TButton", background=[("active", "#1d4ed8")])
        style.configure("Secondary.TButton", padding=(16, 10), relief="flat", background="#e2e8f0", foreground="#0f172a", font=_safe_font(10, "bold"))
        style.map("Secondary.TButton", background=[("active", "#cbd5e1")])
        style.configure("Modern.TEntry", fieldbackground="#ffffff", foreground="#0f172a", bordercolor="#cbd5e1")
        style.configure("Header.TLabel", background="#0f172a", foreground="#f8fafc", font=_safe_font(26, "bold"))
        style.configure("SubHeader.TLabel", background="#0f172a", foreground="#94a3b8", font=_safe_font(11))
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("Card.TLabel", background="#ffffff", foreground="#334155")
        style.configure("Modern.TCheckbutton", background="#f8fafc")

    def _build_login_screen(self):
        self.clear_widgets()

        shell = tk.Frame(self.root, bg="#0f172a")
        shell.pack(fill="both", expand=True)

        left = tk.Frame(shell, bg="#0f172a", width=440)
        left.pack(side="left", fill="y", padx=(0, 0))
        left.pack_propagate(False)

        branding = tk.Frame(left, bg="#0f172a")
        branding.pack(anchor="w", padx=48, pady=(60, 20))

        title = tk.Label(branding, text="Snaglist Pro", bg="#0f172a", fg="#f8fafc", font=_safe_font(30, "bold"))
        title.pack(anchor="w")
        sub = tk.Label(branding, text="Modern defect and snag tracking", bg="#0f172a", fg="#94a3b8", font=_safe_font(12))
        sub.pack(anchor="w", pady=(8, 0))

        right = tk.Frame(shell, bg="#f8fafc")
        right.pack(side="right", fill="both", expand=True)

        form = tk.Frame(right, bg="#f8fafc")
        form.pack(expand=True, padx=60, pady=40)

        tk.Label(form, text="Login", bg="#f8fafc", fg="#0f172a", font=_safe_font(26, "bold")).pack(anchor="w", pady=(0, 18))
        tk.Label(form, text="Username", bg="#f8fafc", fg="#475569", font=_safe_font(10, "bold")).pack(anchor="w")
        self.username_var = tk.StringVar(value=DEFAULT_USERNAME)
        username_entry = tk.Entry(form, textvariable=self.username_var, width=32, font=_safe_font(11), bd=1, relief="solid", highlightthickness=1, highlightbackground="#cbd5e1", highlightcolor="#2563eb")
        username_entry.pack(fill="x", pady=(6, 12))

        tk.Label(form, text="Password", bg="#f8fafc", fg="#475569", font=_safe_font(10, "bold")).pack(anchor="w")
        self.password_var = tk.StringVar(value=DEFAULT_PASSWORD)
        password_entry = tk.Entry(form, textvariable=self.password_var, width=32, show="*", font=_safe_font(11), bd=1, relief="solid", highlightthickness=1, highlightbackground="#cbd5e1", highlightcolor="#2563eb")
        password_entry.pack(fill="x", pady=(6, 18))

        login_btn = tk.Button(form, text="Login", command=self.handle_login, bg="#2563eb", fg="#ffffff", activebackground="#1d4ed8", font=_safe_font(10, "bold"), bd=0, padx=18, pady=10, width=20)
        login_btn.pack(fill="x", pady=(6, 0))

        watermark = tk.Label(
            self.root,
            text="Developed by Vineeth.Bisa",
            fg="#7e7e7e",
            bg="#0f172a",
            font=_safe_font(9),
        )
        watermark.place(relx=1.0, rely=1.0, anchor="se", x=-12, y=-10)

    def _build_main_screen(self):
        self.clear_widgets()

        shell = tk.Frame(self.root, bg="#eef2ff")
        shell.pack(fill="both", expand=True)

        top = tk.Frame(shell, bg="#0f172a", height=130)
        top.pack(fill="x")
        top.pack_propagate(False)

        title = tk.Label(top, text="Snaglist Pro", bg="#0f172a", fg="#f8fafc", font=_safe_font(27, "bold"))
        title.place(x=26, y=24)

        sub = tk.Label(top, text="Construction defect and snag workflow", bg="#0f172a", fg="#94a3b8", font=_safe_font(11))
        sub.place(x=26, y=72)

        actions = tk.Frame(shell, bg="#eef2ff")
        actions.pack(fill="x", padx=20, pady=(18, 12))

        choose_zip_btn = tk.Button(actions, text="Choose ZIP", command=self.choose_zip, bg="#2563eb", fg="#ffffff", activebackground="#1d4ed8", font=_safe_font(10, "bold"), bd=0, padx=18, pady=10)
        choose_zip_btn.pack(side="left")

        choose_checklist_btn = tk.Button(actions, text="Choose Checklist", command=self.choose_checklist, bg="#0f172a", fg="#ffffff", activebackground="#111827", font=_safe_font(10, "bold"), bd=0, padx=18, pady=10)
        choose_checklist_btn.pack(side="left", padx=(10, 0))

        process_btn = tk.Button(actions, text="Generate Snaglist", command=self.process_zip, bg="#0f172a", fg="#ffffff", activebackground="#111827", font=_safe_font(10, "bold"), bd=0, padx=18, pady=10)
        process_btn.pack(side="left", padx=(10, 0))

        self.download_btn = tk.Button(
            actions,
            text="Download Excel/Sheets",
            command=self.download_output,
            bg="#10b981",
            fg="#ffffff",
            activebackground="#059669",
            font=_safe_font(10, "bold"),
            bd=0,
            padx=18,
            pady=10,
            state="disabled",
        )
        self.download_btn.pack(side="left", padx=(10, 0))

        logout_btn = tk.Button(actions, text="Logout", command=self.logout, bg="#e2e8f0", fg="#0f172a", activebackground="#cbd5e1", font=_safe_font(10, "bold"), bd=0, padx=18, pady=10)
        logout_btn.pack(side="right")

        status_frame = tk.Frame(shell, bg="#ffffff", highlightthickness=1, highlightbackground="#dfe7f5")
        status_frame.pack(fill="x", padx=20, pady=(0, 12))
        tk.Label(status_frame, text="Progress status", bg="#ffffff", fg="#0f172a", font=_safe_font(10, "bold"), anchor="w").pack(anchor="w", padx=14, pady=(12, 4))
        self.status_var.set("Ready")
        self.progress_var.set(0)
        status_label = tk.Label(status_frame, textvariable=self.status_var, bg="#ffffff", fg="#2563eb", font=_safe_font(11, "bold"), anchor="w")
        status_label.pack(anchor="w", padx=14, pady=(0, 10))
        progress = ttk.Progressbar(status_frame, variable=self.progress_var, maximum=100, length=420)
        progress.pack(fill="x", padx=14, pady=(0, 12))

        stats = tk.Frame(shell, bg="#eef2ff")
        stats.pack(fill="x", padx=20, pady=(0, 12))

        self.stat_vars = {}
        for idx, (label_text, value_text, accent) in enumerate([
            ("Open Snags", "0", "#2563eb"),
            ("In Progress", "0", "#f59e0b"),
            ("Resolved", "0", "#10b981"),
        ]):
            card = tk.Frame(stats, bg="#ffffff", highlightthickness=1, highlightbackground="#dfe7f5", width=200, height=94)
            card.grid(row=0, column=idx, padx=(0 if idx == 0 else 12, 0), sticky="nsew")
            card.grid_propagate(False)

            accent_bar = tk.Frame(card, bg=accent, height=6)
            accent_bar.pack(fill="x")

            tk.Label(card, text=label_text, bg="#ffffff", fg="#64748b", font=_safe_font(10), anchor="w").pack(anchor="w", padx=14, pady=(12, 4))
            value_label = tk.Label(card, text=value_text, bg="#ffffff", fg="#0f172a", font=_safe_font(22, "bold"), anchor="w")
            value_label.pack(anchor="w", padx=14)
            self.stat_vars[label_text] = value_label

        stats.grid_columnconfigure((0, 1, 2), weight=1)

        card = tk.Frame(shell, bg="#ffffff", highlightthickness=1, highlightbackground="#e2e8f0")
        card.pack(fill="x", padx=20, pady=(0, 14))

        self.zip_label = tk.Label(card, text="No ZIP selected", anchor="w", justify="left", bg="#ffffff", fg="#334155", font=_safe_font(10), padx=16, pady=14)
        self.zip_label.pack(fill="x")

        checklist_card = tk.Frame(shell, bg="#ffffff", highlightthickness=1, highlightbackground="#e2e8f0")
        checklist_card.pack(fill="x", padx=20, pady=(0, 14))
        self.checklist_label = tk.Label(checklist_card, text="No checklist selected", anchor="w", justify="left", bg="#ffffff", fg="#334155", font=_safe_font(10), padx=16, pady=14)
        self.checklist_label.pack(fill="x")

        log_frame = tk.Frame(shell, bg="#ffffff", highlightthickness=1, highlightbackground="#e2e8f0")
        log_frame.pack(fill="both", expand=True, padx=20, pady=(0, 18))

        title_word = tk.Label(log_frame, text="Processing log", bg="#ffffff", fg="#0f172a", font=_safe_font(11, "bold"), anchor="w")
        title_word.pack(anchor="w", padx=14, pady=(12, 6))

        self.log_box = tk.Text(log_frame, height=14, wrap="word", bd=0, padx=12, pady=12, bg="#f8fafc", fg="#0f172a", font=_safe_font(10))
        self.log_box.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.log_box.insert("end", "Ready. Select a WhatsApp ZIP export and checklist to begin.\n")
        self.log_box.config(state="disabled")

        watermark = tk.Label(
            self.root,
            text="Developed by Vineeth.Bisa",
            fg="#7e7e7e",
            bg="#eef2ff",
            font=_safe_font(9),
        )
        watermark.place(relx=1.0, rely=1.0, anchor="se", x=-12, y=-10)

    def clear_widgets(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def handle_login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()

        if username == DEFAULT_USERNAME and password == DEFAULT_PASSWORD:
            self.current_user = username
            self._build_main_screen()
            return

        messagebox.showerror("Login failed", "Invalid username or password.")

    def logout(self):
        self.current_user = None
        self._build_login_screen()

    def choose_zip(self):
        file_path = filedialog.askopenfilename(
            title="Select WhatsApp ZIP export",
            filetypes=[("ZIP Files", "*.zip")],
        )
        if file_path:
            self.selected_zip = file_path
            self.zip_label.config(text=file_path)
            self.append_log(f"Selected ZIP: {file_path}")

    def choose_checklist(self):
        file_path = filedialog.askopenfilename(
            title="Select checklist file",
            filetypes=[("Excel Files", "*.xlsx"), ("CSV Files", "*.csv"), ("All files", "*.*")],
        )
        if file_path:
            self.selected_checklist = file_path
            self.checklist_label.config(text=file_path)
            self.append_log(f"Selected checklist: {file_path}")

    def _set_dashboard_counts(self, total=0, open_count=0, in_progress=0, resolved=0):
        self.stat_vars.get("Open Snags", self.stat_vars.get("Open Snags")).config(text=str(open_count))
        self.stat_vars.get("In Progress", self.stat_vars.get("In Progress")).config(text=str(in_progress))
        self.stat_vars.get("Resolved", self.stat_vars.get("Resolved")).config(text=str(resolved))

    def _update_progress(self, status, pct):
        self.status_var.set(status)
        self.progress_var.set(pct)
        self.root.update_idletasks()

    def process_zip(self):
        if not getattr(self, "selected_zip", None):
            messagebox.showwarning("No ZIP selected", "Please choose a ZIP file first.")
            return
        if not getattr(self, "selected_checklist", None):
            messagebox.showwarning("Checklist missing", "Please choose a checklist file before generating the snaglist.")
            return

        self.latest_output_file = None
        if self.download_btn is not None:
            self.download_btn.config(state="disabled")

        self._update_progress("Preparing ZIP", 10)
        self.append_log("Processing ZIP file...")
        self.append_log(f"Checklist file: {self.selected_checklist}")
        self.root.update_idletasks()

        output_file = self._generate_output_from_zip(self.selected_zip)
        if output_file:
            self.latest_output_file = output_file
            if self.download_btn is not None:
                self.download_btn.config(state="normal")
            self._update_progress("Completed", 100)
            self._set_dashboard_counts(open_count=1, in_progress=1, resolved=0)
            self.append_log(f"Output generated: {output_file}")
            messagebox.showinfo("Output ready", f"Snaglist file created:\n{output_file}")
        else:
            self._update_progress("Failed", 0)
            self.append_log("No readable WhatsApp content found in the ZIP.")
            messagebox.showerror("Processing failed", "No readable WhatsApp data was found in the selected ZIP file.")

    def _generate_output_from_zip(self, zip_path):
        try:
            self._update_progress("Reading ZIP content", 25)
            with zipfile.ZipFile(zip_path, "r") as archive:
                text_files = [
                    name for name in archive.namelist()
                    if name.lower().endswith((".txt", ".csv", ".json", ".log"))
                ]
                if not text_files:
                    return None

                all_rows = []
                total = len(text_files)
                for index, name in enumerate(text_files, start=1):
                    self._update_progress(f"Parsing file {index}/{total}", 25 + int((index / total) * 40))
                    with archive.open(name) as handle:
                        raw = handle.read().decode("utf-8", errors="replace")
                    parsed_rows = parse_whatsapp_text(raw)
                    all_rows.extend(parsed_rows)

                if not all_rows:
                    return None

                self._update_progress("Writing report", 75)
                output_dir = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "SnaglistPro" / "exports"
                output_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = output_dir / f"snaglist_report_{timestamp}.xlsx"

                workbook = Workbook()
                sheet = workbook.active
                sheet.title = "Snaglist"
                headers = ["Date", "Time", "Sender", "Message", "Has Media", "Media Files"]
                sheet.append(headers)
                for row in all_rows:
                    sheet.append([
                        row.get("date", ""),
                        row.get("time", ""),
                        row.get("sender", ""),
                        row.get("message", ""),
                        "Yes" if row.get("has_media", False) else "No",
                        "; ".join(row.get("media_files", [])),
                    ])

                for column_cells in sheet.columns:
                    max_length = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
                    sheet.column_dimensions[column_cells[0].column_letter].width = min(max_length + 2, 40)

                workbook.save(output_file)
                return str(output_file)
        except Exception as exc:
            self._update_progress("Error", 0)
            messagebox.showerror("ZIP processing failed", str(exc))
            return None

    def download_output(self):
        if not getattr(self, "latest_output_file", None):
            messagebox.showinfo("No file ready", "Generate a snaglist first before downloading.")
            return

        source_path = Path(self.latest_output_file)
        if not source_path.exists():
            messagebox.showerror("Missing file", f"The generated file no longer exists:\n{source_path}")
            return

        target_path = filedialog.asksaveasfilename(
            title="Save snaglist output",
            defaultextension=".xlsx",
            initialfile=source_path.name.replace(".csv", ".xlsx").replace(".xls", ".xlsx"),
            filetypes=[("Excel/Google Sheets Files", "*.xlsx"), ("CSV Files", "*.csv"), ("All files", "*.*")],
        )
        if not target_path:
            return

        try:
            with source_path.open("rb") as src, open(target_path, "wb") as dst:
                dst.write(src.read())
            self.append_log(f"Downloaded output to: {target_path}")
            messagebox.showinfo("Download complete", f"File saved to:\n{target_path}")
        except Exception as exc:
            messagebox.showerror("Download failed", str(exc))

    def append_log(self, message):
        if not hasattr(self, "log_box"):
            return
        self.log_box.config(state="normal")
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")
        self.log_box.config(state="disabled")


def run_desktop_app():
    root = tk.Tk()
    app = SnaglistDesktopApp(root)
    root.mainloop()


if __name__ == "__main__":
    run_desktop_app()
