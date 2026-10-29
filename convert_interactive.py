#!/usr/bin/env python3
"""
Jonathan Rothberg's MineCraft to LEGO converter

Window for picking a schematic and writing a LEGO file plus a printable STL.
"""

import os
import sys
import glob
import queue
import threading
import subprocess
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from minecraft_to_lego_converter import MinecraftToLegoConverter


def schematics_dir():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "schematics")


def models_dir():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
    os.makedirs(path, exist_ok=True)
    return path


def list_schematic_files():
    folder = schematics_dir()
    os.makedirs(folder, exist_ok=True)
    found = []
    for pattern in ("*.schematic", "*.SCHEMATIC", "*.schem", "*.SCHEM"):
        found.extend(glob.glob(os.path.join(folder, pattern)))
    # A file chosen from somewhere else is added by the window; this is the folder list.
    return sorted(set(found))


class ConverterWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Minecraft to LEGO")
        self.root.minsize(760, 640)
        self.root.geometry("860x700")
        self.messages = queue.Queue()
        self.worker = None
        self.last_ldr = None
        self.last_stl = None
        self.extra_files = []

        self._build()
        self.refresh_files()
        self.root.after(100, self._drain_messages)

    def _build(self):
        pad = {"padx": 14, "pady": 6}
        header = ttk.Frame(self.root)
        header.pack(fill="x", **pad)
        ttk.Label(header, text="Minecraft to LEGO", font=("Helvetica", 22, "bold")).pack(anchor="w")
        ttk.Label(
            header,
            text="Turns a schematic into bricks you can assemble, and an STL you can print.",
            wraplength=780,
        ).pack(anchor="w", pady=(2, 0))

        body = ttk.Frame(self.root)
        body.pack(fill="both", expand=True, padx=14, pady=4)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        files = ttk.LabelFrame(body, text="Schematic")
        files.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.file_list = tk.Listbox(files, height=14, activestyle="dotbox", exportselection=False)
        self.file_list.pack(fill="both", expand=True, padx=8, pady=8)
        self.file_list.bind("<<ListboxSelect>>", self._on_select)
        file_buttons = ttk.Frame(files)
        file_buttons.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(file_buttons, text="Refresh", command=self.refresh_files).pack(side="left")
        ttk.Button(file_buttons, text="Choose a file…", command=self.choose_file).pack(side="left", padx=8)

        options = ttk.LabelFrame(body, text="Build")
        options.grid(row=0, column=1, sticky="nsew")
        self.scale_2x = tk.BooleanVar(value=True)
        self.optimize = tk.BooleanVar(value=True)
        self.write_ldr = tk.BooleanVar(value=True)
        self.write_stl = tk.BooleanVar(value=True)

        ttk.Checkbutton(options, text="2× scale  —  steps, slopes, and overhangs", variable=self.scale_2x).pack(anchor="w", padx=10, pady=(10, 0))
        ttk.Label(
            options,
            text="Each Minecraft block becomes 2 studs wide and 2 bricks tall. Stairs get a real step. A straight stair with nothing on top becomes a slope. A block sticking out is joined to the brick that holds it.",
            wraplength=360,
        ).pack(anchor="w", padx=28, pady=(2, 8))
        ttk.Checkbutton(options, text="Merge matching bricks  —  fewer pieces", variable=self.optimize).pack(anchor="w", padx=10)
        ttk.Label(
            options,
            text="Neighboring blocks of the same color become one longer brick. Overhangs are joined either way.",
            wraplength=360,
        ).pack(anchor="w", padx=28, pady=(2, 8))
        ttk.Checkbutton(options, text="LEGO file  (.ldr)", variable=self.write_ldr).pack(anchor="w", padx=10, pady=(4, 0))
        ttk.Checkbutton(options, text="Printable STL", variable=self.write_stl).pack(anchor="w", padx=10)

        name_row = ttk.Frame(options)
        name_row.pack(fill="x", padx=10, pady=(12, 4))
        ttk.Label(name_row, text="Name").pack(side="left")
        self.name_var = tk.StringVar()
        ttk.Entry(name_row, textvariable=self.name_var).pack(side="left", fill="x", expand=True, padx=(8, 0))
        ttk.Label(options, text="Saved in the models folder.", foreground="#444").pack(anchor="w", padx=10)

        self.convert_button = ttk.Button(options, text="Convert", command=self.convert)
        self.convert_button.pack(fill="x", padx=10, pady=14)

        open_row = ttk.Frame(options)
        open_row.pack(fill="x", padx=10, pady=(0, 10))
        self.open_ldr_button = ttk.Button(open_row, text="Open LEGO file", command=self.open_ldr, state="disabled")
        self.open_ldr_button.pack(side="left")
        self.open_stl_button = ttk.Button(open_row, text="Open STL", command=self.open_stl, state="disabled")
        self.open_stl_button.pack(side="left", padx=8)
        self.reveal_button = ttk.Button(open_row, text="Show in Finder", command=self.reveal, state="disabled")
        self.reveal_button.pack(side="left")

        log_frame = ttk.LabelFrame(self.root, text="Progress")
        log_frame.pack(fill="both", expand=True, padx=14, pady=(4, 12))
        self.log = tk.Text(log_frame, height=10, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True, padx=8, pady=8)

    def _log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def refresh_files(self):
        paths = list_schematic_files()
        # Keep a file the user picked from outside the folder.
        for extra in self.extra_files:
            if extra not in paths and os.path.exists(extra):
                paths.append(extra)
        self.paths = paths
        self.file_list.delete(0, "end")
        if not paths:
            self.file_list.insert("end", "No schematics yet — use Choose a file…")
            self._log("Put .schematic or .schem files in the schematics folder, or choose one.")
            return
        for path in paths:
            try:
                stat = os.stat(path)
                size = stat.st_size / 1024
                when = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                label = f"{os.path.basename(path)}    {size:.0f} KB    {when}"
            except OSError:
                label = os.path.basename(path)
            self.file_list.insert("end", label)
        self.file_list.selection_set(0)
        self._on_select()

    def choose_file(self):
        path = filedialog.askopenfilename(
            title="Choose a Minecraft schematic",
            filetypes=[("Minecraft schematics", "*.schem *.schematic"), ("All files", "*.*")],
        )
        if not path:
            return
        if path not in self.extra_files:
            self.extra_files.append(path)
        self.refresh_files()
        if path in self.paths:
            index = self.paths.index(path)
            self.file_list.selection_clear(0, "end")
            self.file_list.selection_set(index)
            self.file_list.see(index)
            self._on_select()

    def _selected_path(self):
        if not getattr(self, "paths", None):
            return None
        picked = self.file_list.curselection()
        if not picked:
            return None
        index = picked[0]
        if index >= len(self.paths):
            return None
        return self.paths[index]

    def _on_select(self, _event=None):
        path = self._selected_path()
        if not path:
            return
        base = os.path.splitext(os.path.basename(path))[0]
        self.name_var.set(base)

    def convert(self):
        if self.worker and self.worker.is_alive():
            return
        path = self._selected_path()
        if not path:
            messagebox.showinfo("Choose a schematic", "Select a schematic file first.")
            return
        if not self.write_ldr.get() and not self.write_stl.get():
            messagebox.showinfo("Choose an output", "Turn on the LEGO file, the STL, or both.")
            return
        name = self.name_var.get().strip() or os.path.splitext(os.path.basename(path))[0]
        for suffix in (".ldr", ".stl", ".schem", ".schematic"):
            if name.lower().endswith(suffix):
                name = name[: -len(suffix)]
        ldr_path = os.path.join(models_dir(), name + ".ldr") if self.write_ldr.get() else None
        stl_path = os.path.join(models_dir(), name + ".stl") if self.write_stl.get() else None
        existing = [p for p in (ldr_path, stl_path) if p and os.path.exists(p)]
        if existing:
            names = ", ".join(os.path.basename(p) for p in existing)
            if not messagebox.askyesno("Replace files?", f"{names} already exists. Replace it?"):
                return

        self.convert_button.configure(state="disabled")
        self.open_ldr_button.configure(state="disabled")
        self.open_stl_button.configure(state="disabled")
        self.reveal_button.configure(state="disabled")
        self._log("")
        self._log(f"Converting {os.path.basename(path)}")
        scale = 2 if self.scale_2x.get() else 1
        if scale == 1:
            self._log("1× keeps one brick per block. Stairs will not have steps. 2× is the one to print and to build.")

        def work():
            try:
                converter = MinecraftToLegoConverter()

                def progress(msg):
                    self.messages.put(("log", msg))

                schematic = converter.load_schematic(path)
                if schematic is None:
                    self.messages.put(("fail", "Could not read that schematic."))
                    return
                model = converter.build_model(
                    schematic, optimize=self.optimize.get(), scale=scale, progress=progress)
                if ldr_path:
                    converter.save_ldraw_file(model["ldraw"], ldr_path)
                if stl_path:
                    progress("Building the printable mesh…")
                    converter.write_stl(stl_path, model)
                self.messages.put(("done", {"ldr": ldr_path, "stl": stl_path, "stats": model["stats"], "warnings": model["warnings"]}))
            except Exception as exc:
                self.messages.put(("fail", str(exc)))

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def _drain_messages(self):
        try:
            while True:
                kind, payload = self.messages.get_nowait()
                if kind == "log":
                    self._log(payload)
                elif kind == "fail":
                    self._log(payload)
                    self.convert_button.configure(state="normal")
                    messagebox.showerror("Conversion failed", payload)
                elif kind == "done":
                    self.last_ldr = payload["ldr"]
                    self.last_stl = payload["stl"]
                    stats = payload["stats"]
                    self._log(f"Done. {stats['bricks']} pieces, {stats['slopes']} slopes, {stats['anchored']} overhangs joined.")
                    for note in payload["warnings"]:
                        self._log(note)
                    if self.last_ldr:
                        self._log(f"LEGO file: {self.last_ldr}")
                        self.open_ldr_button.configure(state="normal")
                    if self.last_stl:
                        self._log(f"STL: {self.last_stl}")
                        self.open_stl_button.configure(state="normal")
                    self.reveal_button.configure(state="normal")
                    self.convert_button.configure(state="normal")
        except queue.Empty:
            pass
        self.root.after(100, self._drain_messages)

    def _open_path(self, path, stl=False):
        if not path or not os.path.exists(path):
            return
        if stl:
            # fstl is the small viewer. MeshLab is what we install when fstl
            # has no Mac build. open -a wants the .app path for this MeshLab.
            if self._app_exists("fstl"):
                subprocess.Popen(["open", "-a", "fstl", path])
                return
            meshlab = "/Applications/MeshLab2025.07.app"
            if os.path.isdir(meshlab) or self._app_exists("MeshLab"):
                subprocess.Popen(["open", "-a", meshlab if os.path.isdir(meshlab) else "MeshLab", path])
                return
        subprocess.Popen(["open", path])

    def _app_exists(self, name):
        if os.path.isdir(f"/Applications/{name}.app"):
            return True
        try:
            result = subprocess.run(["mdfind", f"kMDItemFSName == '{name}.app'"], capture_output=True, text=True)
            return bool(result.stdout.strip())
        except OSError:
            return False

    def open_ldr(self):
        self._open_path(self.last_ldr)

    def open_stl(self):
        self._open_path(self.last_stl, stl=True)

    def reveal(self):
        path = self.last_stl or self.last_ldr
        if path and os.path.exists(path):
            subprocess.Popen(["open", "-R", path])


def main():
    root = tk.Tk()
    # Ask the Mac theme for a normal window, not a gray utility panel.
    try:
        style = ttk.Style()
        if "aqua" in style.theme_names():
            style.theme_use("aqua")
    except tk.TclError:
        pass
    ConverterWindow(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
