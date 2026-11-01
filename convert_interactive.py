#!/usr/bin/env python3
"""
Jonathan Rothberg's MineCraft to LEGO converter

Window for picking a schematic and writing a LEGO file plus a printable STL.
"""

import os
import sys
import glob
import queue
import re
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
        self.last_bambu = None
        self.loaded_spools = None
        self.loaded_bambu_path = None
        self.extra_files = []

        self._build()
        self._show_spool_plan()
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
        self.write_bambu = tk.BooleanVar(value=False)
        self.bambu_colors = tk.IntVar(value=4)

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
        ttk.Checkbutton(
            options,
            text="Bambu Studio (.3mf)  —  colors stay lined up",
            variable=self.write_bambu,
            command=self._toggle_bambu,
        ).pack(anchor="w", padx=10, pady=(4, 0))
        color_row = ttk.Frame(options)
        color_row.pack(fill="x", padx=28, pady=(2, 0))
        ttk.Label(color_row, text="Filaments").pack(side="left")
        self.color_spin = ttk.Spinbox(
            color_row, from_=1, to=8, textvariable=self.bambu_colors, width=3, state="disabled",
        )
        self.color_spin.pack(side="left", padx=(8, 0))
        self.load_bambu_button = ttk.Button(color_row, text="Load Bambu file…", command=self.load_bambu)
        self.load_bambu_button.pack(side="left", padx=(8, 0))
        self.save_spools_button = ttk.Button(
            color_row, text="Save spools", command=self.save_spools, state="disabled",
        )
        self.save_spools_button.pack(side="left", padx=(8, 0))
        ttk.Label(
            options,
            text="Suggested spool color is shown below. Load an 8-color Bambu file, lower the number, and Save spools.",
            wraplength=360,
        ).pack(anchor="w", padx=28, pady=(2, 2))
        ttk.Label(options, text="Suggested spools", font=("Helvetica", 13, "bold")).pack(anchor="w", padx=28)
        self.spool_frame = ttk.Frame(options)
        self.spool_frame.pack(fill="x", padx=28, pady=(0, 4))
        self.bambu_colors.trace_add("write", self._on_color_count)

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
        self.open_bambu_button = ttk.Button(open_row, text="Open in Bambu", command=self.open_bambu, state="disabled")
        self.open_bambu_button.pack(side="left", padx=8)
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

    def _toggle_bambu(self):
        self._sync_color_spin()

    def _sync_color_spin(self):
        enabled = self.write_bambu.get() or bool(self.loaded_spools)
        self.color_spin.configure(state="normal" if enabled else "disabled")
        self.save_spools_button.configure(state="normal" if self.loaded_spools else "disabled")

    def _on_color_count(self, *_args):
        if self.loaded_spools:
            self._show_spool_plan()

    def _show_spool_plan(self):
        for child in self.spool_frame.winfo_children():
            child.destroy()
        if not self.loaded_spools:
            ttk.Label(self.spool_frame, text="Load a Bambu file to see the spool colors.").pack(anchor="w")
            return
        converter = MinecraftToLegoConverter()
        groups = converter.plan_spool_groups(self.loaded_spools, self._filament_count())
        for slot, members in enumerate(groups, start=1):
            anchor = max(members, key=lambda spool: len(spool["faces"]))
            also = []
            for member in members:
                if member is not anchor:
                    also.append(member["label"])
                also.extend(member.get("also") or [])
            seen = []
            for name in also:
                if name and name != anchor["label"] and name not in seen:
                    seen.append(name)
            text = f"Spool {slot}   {anchor['label']}"
            if seen:
                text += "  —  also " + ", ".join(seen)
            row = ttk.Frame(self.spool_frame)
            row.pack(fill="x", pady=1)
            red, green, blue = anchor["rgb"]
            swatch = tk.Canvas(row, width=18, height=18, highlightthickness=1, highlightbackground="#888")
            swatch.pack(side="left")
            swatch.create_rectangle(1, 1, 17, 17, fill=f"#{red:02x}{green:02x}{blue:02x}", outline="")
            ttk.Label(row, text=text).pack(side="left", padx=6)

    def load_bambu(self):
        if self.worker and self.worker.is_alive():
            return
        path = filedialog.askopenfilename(
            title="Choose a Bambu 3MF",
            filetypes=[("Bambu 3MF", "*.3mf"), ("All files", "*.*")],
        )
        if not path:
            return
        self.load_bambu_button.configure(state="disabled")
        self._log("")
        self._log(f"Reading {os.path.basename(path)}")

        def work():
            try:
                spools = MinecraftToLegoConverter().read_bambu(path)
                self.messages.put(("spools", {"path": path, "spools": spools}))
            except Exception as exc:
                self.messages.put(("fail", str(exc)))
            finally:
                self.messages.put(("load_ready", None))

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def save_spools(self):
        if self.worker and self.worker.is_alive():
            return
        if not self.loaded_spools:
            messagebox.showinfo("Load a Bambu file", "Load the 8-color Bambu file first.")
            return
        count = self._filament_count()
        folder = os.path.dirname(self.loaded_bambu_path or models_dir())
        stem = os.path.splitext(os.path.basename(self.loaded_bambu_path or "model.3mf"))[0]
        stem = re.sub(r"-\d+$", "", stem)
        path = filedialog.asksaveasfilename(
            title="Save the regrouped Bambu file",
            initialdir=folder,
            initialfile=f"{stem}-{count}.3mf",
            defaultextension=".3mf",
            filetypes=[("Bambu 3MF", "*.3mf")],
        )
        if not path:
            return
        self.save_spools_button.configure(state="disabled")
        self._log(f"Saving {count} spools…")
        spools = self.loaded_spools

        def work():
            try:
                notes = MinecraftToLegoConverter().save_regrouped_bambu(path, spools, count)
                fresh = MinecraftToLegoConverter().read_bambu(path)
                self.messages.put(("spools", {"path": path, "spools": fresh, "notes": notes}))
            except Exception as exc:
                self.messages.put(("fail", str(exc)))

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def _filament_count(self):
        try:
            count = int(self.bambu_colors.get())
        except (tk.TclError, ValueError):
            count = 4
        return max(1, min(8, count))

    def convert(self):
        if self.worker and self.worker.is_alive():
            return
        path = self._selected_path()
        if not path:
            messagebox.showinfo("Choose a schematic", "Select a schematic file first.")
            return
        if not self.write_ldr.get() and not self.write_stl.get() and not self.write_bambu.get():
            messagebox.showinfo("Choose an output", "Turn on the LEGO file, the STL, the Bambu file, or any of them.")
            return
        name = self.name_var.get().strip() or os.path.splitext(os.path.basename(path))[0]
        for suffix in (".ldr", ".stl", ".3mf", ".schem", ".schematic"):
            if name.lower().endswith(suffix):
                name = name[: -len(suffix)]
        ldr_path = os.path.join(models_dir(), name + ".ldr") if self.write_ldr.get() else None
        stl_path = os.path.join(models_dir(), name + ".stl") if self.write_stl.get() else None
        bambu_path = os.path.join(models_dir(), name + ".3mf") if self.write_bambu.get() else None
        filament_count = self._filament_count()
        existing = [p for p in (ldr_path, stl_path, bambu_path) if p and os.path.exists(p)]
        if existing:
            names = ", ".join(os.path.basename(p) for p in existing)
            if not messagebox.askyesno("Replace files?", f"{names} already exists. Replace it?"):
                return

        self.convert_button.configure(state="disabled")
        self.open_ldr_button.configure(state="disabled")
        self.open_stl_button.configure(state="disabled")
        self.open_bambu_button.configure(state="disabled")
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
                bambu_notes = []
                spools = None
                if bambu_path:
                    progress(f"Building the Bambu file with {filament_count} filaments…")
                    bambu_notes = converter.write_bambu(bambu_path, model, filament_count)
                    progress("Reading the spool colors…")
                    spools = converter.read_bambu(bambu_path)
                fit_note = getattr(converter, "print_fit_note", "")
                if fit_note and fit_note not in bambu_notes:
                    progress(fit_note)
                self.messages.put(("done", {
                    "ldr": ldr_path,
                    "stl": stl_path,
                    "bambu": bambu_path,
                    "bambu_notes": bambu_notes,
                    "spools": spools,
                    "stats": model["stats"],
                    "warnings": model["warnings"],
                }))
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
                    self.load_bambu_button.configure(state="normal")
                    self._sync_color_spin()
                    messagebox.showerror("Conversion failed", payload)
                elif kind == "load_ready":
                    self.load_bambu_button.configure(state="normal")
                elif kind == "spools":
                    self.loaded_spools = payload["spools"]
                    self.loaded_bambu_path = payload["path"]
                    self.last_bambu = payload["path"]
                    self._sync_color_spin()
                    self._show_spool_plan()
                    self.open_bambu_button.configure(state="normal")
                    self.reveal_button.configure(state="normal")
                    self.load_bambu_button.configure(state="normal")
                    for note in payload.get("notes") or []:
                        self._log(note)
                    self._log(f"Bambu file: {payload['path']}")
                elif kind == "done":
                    self.last_ldr = payload["ldr"]
                    self.last_stl = payload["stl"]
                    self.last_bambu = payload.get("bambu")
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
                    if self.last_bambu:
                        for note in payload.get("bambu_notes") or []:
                            self._log(note)
                        self._log(f"Bambu file: {self.last_bambu}")
                        self.open_bambu_button.configure(state="normal")
                        if payload.get("spools"):
                            self.loaded_spools = payload["spools"]
                            self.loaded_bambu_path = self.last_bambu
                            self._sync_color_spin()
                            self._show_spool_plan()
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

    def open_bambu(self):
        path = self.last_bambu
        if not path or not os.path.exists(path):
            return
        app = "/Applications/BambuStudio.app"
        if os.path.isdir(app):
            subprocess.Popen(["open", "-a", app, path])
            return
        subprocess.Popen(["open", path])

    def reveal(self):
        path = self.last_bambu or self.last_stl or self.last_ldr
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
