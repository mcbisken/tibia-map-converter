# gui.py — OTBM Item Remapper. tkinter front-end over convert.convert() (classic
# OTB->OTB) and convert.convert_to_canary() (source items.xml -> appearances.dat).
import os, sys, threading, traceback
import tkinter as tk
from tkinter import filedialog, ttk
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import convert

APP_TITLE = "OTBM Item Remapper"

class App:
    def __init__(self, root):
        self.root = root
        root.title(APP_TITLE)
        root.geometry("800x580")
        self.mode = tk.StringVar(value="classic")
        self.map_var = tk.StringVar()
        self.src_otb_var = tk.StringVar()
        self.dst_otb_var = tk.StringVar()
        self.src_xml_var = tk.StringVar()      # classic: optional; canary: source names
        self.appearances_var = tk.StringVar()
        self.prefer_id_var = tk.BooleanVar(value=False)
        self.out_var = tk.StringVar()

        bar = ttk.Frame(root)
        bar.grid(row=0, column=0, columnspan=3, sticky="w", padx=8, pady=(8, 2))
        ttk.Label(bar, text="Target:").pack(side="left")
        ttk.Radiobutton(bar, text="items.otb (classic)", variable=self.mode,
                        value="classic", command=self._render).pack(side="left", padx=6)
        ttk.Radiobutton(bar, text="Canary appearances.dat", variable=self.mode,
                        value="canary", command=self._render).pack(side="left", padx=6)

        self.rows = ttk.Frame(root)
        self.rows.grid(row=1, column=0, columnspan=3, sticky="ew")
        root.grid_columnconfigure(0, weight=1)

        self.btn = ttk.Button(root, text="Convert", command=self._start)
        self.btn.grid(row=2, column=0, columnspan=3, pady=8)
        self.log = tk.Text(root, height=18, wrap="word")
        self.log.grid(row=3, column=0, columnspan=3, sticky="nsew", padx=8, pady=4)
        root.grid_rowconfigure(3, weight=1)
        self._render()

    def _render(self):
        for w in self.rows.winfo_children():
            w.destroy()
        self.rows.grid_columnconfigure(1, weight=1)
        r = 0
        self._file_row("Map (.otbm):", self.map_var, r,
                       [("OTBM map", "*.otbm"), ("All files", "*.*")], self._on_map_chosen); r += 1
        if self.mode.get() == "classic":
            self._file_row("Source items.otb (old):", self.src_otb_var, r,
                           [("OTB", "*.otb"), ("All files", "*.*")]); r += 1
            self._file_row("Target items.otb (new):", self.dst_otb_var, r,
                           [("OTB", "*.otb"), ("All files", "*.*")]); r += 1
            self._file_row("Source items.xml (optional):", self.src_xml_var, r,
                           [("XML", "*.xml"), ("All files", "*.*")]); r += 1
        else:
            self._file_row("Source items.xml (old):", self.src_xml_var, r,
                           [("XML", "*.xml"), ("All files", "*.*")]); r += 1
            self._file_row("Target appearances.dat (Canary):", self.appearances_var, r,
                           [("appearances.dat", "*.dat"), ("All files", "*.*")]); r += 1
            ttk.Checkbutton(self.rows, variable=self.prefer_id_var,
                            text="Same-era source: match by ID first (keep ids that "
                                 "already exist in Canary)").grid(
                row=r, column=1, columnspan=2, sticky="w", padx=4, pady=2); r += 1
        self._dir_row("Output folder:", self.out_var, r); r += 1

    def _file_row(self, label, var, row, filetypes, on_set=None):
        f = self.rows
        ttk.Label(f, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(f, textvariable=var).grid(row=row, column=1, sticky="ew", padx=4)
        def browse():
            path = filedialog.askopenfilename(filetypes=filetypes)
            if path:
                var.set(path)
                if on_set:
                    on_set(path)
        ttk.Button(f, text="Browse...", command=browse).grid(row=row, column=2, padx=8)

    def _dir_row(self, label, var, row):
        f = self.rows
        ttk.Label(f, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(f, textvariable=var).grid(row=row, column=1, sticky="ew", padx=4)
        def browse():
            path = filedialog.askdirectory()
            if path:
                var.set(path)
        ttk.Button(f, text="Browse...", command=browse).grid(row=row, column=2, padx=8)

    def _on_map_chosen(self, path):
        if not self.out_var.get():
            self.out_var.set(os.path.join(os.path.dirname(path), "converted"))

    def _write(self, msg):
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.root.update_idletasks()

    def _start(self):
        self.btn.config(state="disabled")
        self.log.delete("1.0", "end")
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            mode = self.mode.get()
            m, out = self.map_var.get(), self.out_var.get()
            if mode == "classic":
                s, d = self.src_otb_var.get(), self.dst_otb_var.get()
                if not (m and s and d and out):
                    self._write("ERROR: Map, both items.otb files, and output folder are required.")
                    return
                xml = self.src_xml_var.get() or None
                summary = convert.convert(m, s, d, out, src_xml=xml, log=self._write)
                self._write("")
                self._write(f"SUCCESS: matches={summary.matches} customs={summary.customs} "
                            f"ambiguous={summary.ambiguous} unanchored={summary.unanchored} "
                            f"changed={summary.changed}")
                self._write(f"Converted map: {summary.out_map}")
                if summary.customs:
                    self._write(f"New items.otb (with relocated customs): {summary.out_otb}")
            else:
                x, a = self.src_xml_var.get(), self.appearances_var.get()
                if not (m and x and a and out):
                    self._write("ERROR: Map, source items.xml, target appearances.dat, "
                                "and output folder are required.")
                    return
                summary = convert.convert_to_canary(m, x, a, out, log=self._write,
                                                    prefer_id=self.prefer_id_var.get())
                self._write("")
                self._write(f"SUCCESS: id_matched={summary.id_matched} exact={summary.exact} "
                            f"ambiguous={summary.ambiguous} unmatched={summary.unmatched} "
                            f"changed={summary.changed}")
                self._write(f"Converted map: {summary.out_map}")
                self._write(f"Review report: {summary.out_report}")
        except Exception as e:
            self._write("")
            self._write(f"FAILED: {e}")
            self._write(traceback.format_exc())
            self._write("No partial map was written.")
        finally:
            self.root.after(0, lambda: self.btn.config(state="normal"))

def main():
    root = tk.Tk()
    App(root)
    root.mainloop()

if __name__ == "__main__":
    main()
