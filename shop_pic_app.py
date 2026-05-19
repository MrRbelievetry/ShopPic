import os
import json
import math
from io import BytesIO
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageOps, ImageFilter

APP_NAME = "Shop Pic"
MAX_IMAGES = 10
MAX_SIZE_BYTES = 5 * 1024 * 1024
ACCEPTED_EXT = {".jpg", ".jpeg", ".png"}
INVALID_CHARS = set('<>:"/\\|?*')

BG = "#f7f2e9"
CARD = "#ffffff"
TEXT = "#2f2f2f"
MUTED = "#6b6b6b"
GOLD = "#c8a65a"
GOLD_DARK = "#a9873f"
RED = "#b94a48"
GREEN = "#4d8b57"


def app_config_path() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    folder = Path(base) / "Shop Pic"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "config.json"


def load_config():
    path = app_config_path()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_config(cfg):
    app_config_path().write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def human_size(n: int) -> str:
    if n < 1024:
        return f"{n} o"
    if n < 1024 * 1024:
        return f"{n / 1024:.0f} Ko"
    return f"{n / (1024 * 1024):.2f} Mo"


def validate_final_name(name: str) -> str:
    cleaned = name.strip()
    if cleaned.lower().endswith(".jpg"):
        cleaned = cleaned[:-4]
    elif cleaned.lower().endswith(".jpeg"):
        cleaned = cleaned[:-5]
    if not cleaned:
        raise ValueError("Un nom de fichier est vide.")
    if any(ch in INVALID_CHARS for ch in cleaned):
        raise ValueError(f"Le nom de fichier contient un caractère interdit : {cleaned}")
    if cleaned.endswith(".") or cleaned.endswith(" "):
        raise ValueError(f"Le nom de fichier se termine par un point ou un espace : {cleaned}")
    return cleaned + ".jpg"


class ImageRow:
    def __init__(self, parent, path: Path, index: int):
        self.path = path
        self.frame = tk.Frame(parent, bg=CARD, highlightthickness=1, highlightbackground="#e4dccf")
        self.frame.grid_columnconfigure(2, weight=1)
        self.thumb_label = tk.Label(self.frame, bg=CARD, width=70, height=70)
        self.thumb_label.grid(row=0, column=0, rowspan=2, padx=8, pady=6)
        self.name_label = tk.Label(self.frame, text=path.name, bg=CARD, fg=TEXT, anchor="w", font=("Segoe UI", 9, "bold"))
        self.name_label.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(0,8), pady=(6,0))
        self.status_label = tk.Label(self.frame, text="", bg=CARD, fg=MUTED, anchor="w", font=("Segoe UI", 8))
        self.status_label.grid(row=1, column=1, sticky="w", padx=(0,8), pady=(0,6))
        self.entry = tk.Entry(self.frame, font=("Segoe UI", 10), relief="solid", bd=1)
        self.entry.grid(row=1, column=2, sticky="ew", padx=(4,8), pady=(0,6))
        self.entry.insert(0, path.stem)
        self.valid = True
        self.photo = None
        self.check_and_load_thumbnail()

    def check_and_load_thumbnail(self):
        size = self.path.stat().st_size
        ext = self.path.suffix.lower()
        if ext not in ACCEPTED_EXT:
            self.valid = False
            self.status_label.config(text="Format refusé", fg=RED)
            return
        if size > MAX_SIZE_BYTES:
            self.valid = False
            self.status_label.config(text=f"Refusée : {human_size(size)} > 5 Mo", fg=RED)
            return
        try:
            with Image.open(self.path) as im:
                w, h = im.size
                if w != h:
                    self.valid = False
                    self.status_label.config(text=f"Refusée : image non carrée ({w}×{h})", fg=RED)
                else:
                    self.status_label.config(text=f"OK — {w}×{h} — {human_size(size)}", fg=GREEN)
                thumb = ImageOps.exif_transpose(im.copy())
                thumb.thumbnail((68, 68), Image.Resampling.LANCZOS)
                canvas = Image.new("RGB", (70, 70), "white")
                canvas.paste(thumb.convert("RGB"), ((70-thumb.width)//2, (70-thumb.height)//2))
                self.photo = ImageTk.PhotoImage(canvas)
                self.thumb_label.config(image=self.photo)
        except Exception:
            self.valid = False
            self.status_label.config(text="Impossible de lire cette image", fg=RED)


class ShopPicApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("900x650")
        self.minsize(820, 580)
        self.configure(bg=BG)
        self.rows = []
        self.cfg = load_config()
        self.export_dir = self.cfg.get("export_dir")
        icon_path = Path(__file__).with_name("shop_pic.ico")
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass
        self.build_ui()
        if not self.export_dir or not Path(self.export_dir).exists():
            self.after(300, self.choose_export_first_launch)

    def build_ui(self):
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=18, pady=(14,8))
        tk.Label(header, text="Shop Pic", bg=BG, fg=TEXT, font=("Segoe UI", 22, "bold")).pack(side="left")
        tk.Label(header, text="Préparation rapide des images produits", bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(side="left", padx=14, pady=(8,0))

        controls = tk.Frame(self, bg=CARD, highlightthickness=1, highlightbackground="#e4dccf")
        controls.pack(fill="x", padx=18, pady=8)
        controls.grid_columnconfigure(3, weight=1)

        self.add_btn = tk.Button(controls, text="Ajouter des images", command=self.add_images, bg=GOLD, fg="white", activebackground=GOLD_DARK, relief="flat", font=("Segoe UI", 11, "bold"), padx=18, pady=8)
        self.add_btn.grid(row=0, column=0, padx=12, pady=12)
        self.clear_btn = tk.Button(controls, text="Vider", command=self.clear_images, bg="#eee6d8", fg=TEXT, activebackground="#e0d5c4", relief="flat", font=("Segoe UI", 10), padx=14, pady=8)
        self.clear_btn.grid(row=0, column=1, padx=(0,12), pady=12)

        self.mode = tk.StringVar(value="prestashop")
        mode_frame = tk.Frame(controls, bg=CARD)
        mode_frame.grid(row=0, column=2, padx=12, pady=8, sticky="w")
        tk.Label(mode_frame, text="Format :", bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        ttk.Radiobutton(mode_frame, text="PrestaShop 800×800", variable=self.mode, value="prestashop").pack(side="left")
        ttk.Radiobutton(mode_frame, text="Amazon 1200×1200", variable=self.mode, value="amazon").pack(side="left", padx=(16,0))

        export_frame = tk.Frame(controls, bg=CARD)
        export_frame.grid(row=0, column=3, sticky="e", padx=12, pady=8)
        self.export_label = tk.Label(export_frame, text="", bg=CARD, fg=MUTED, font=("Segoe UI", 8), anchor="e")
        self.export_label.pack(anchor="e")
        tk.Button(export_frame, text="Changer le dossier", command=self.choose_export_dir, bg="#f4efe7", fg=TEXT, relief="flat", font=("Segoe UI", 9), padx=10, pady=5).pack(anchor="e", pady=(4,0))
        self.update_export_label()

        info = tk.Label(self, text="JPG / JPEG / PNG uniquement • image carrée obligatoire • 5 Mo maximum par image • métadonnées supprimées", bg=BG, fg=MUTED, font=("Segoe UI", 9))
        info.pack(fill="x", padx=22, pady=(2,6))

        list_wrap = tk.Frame(self, bg=BG)
        list_wrap.pack(fill="both", expand=True, padx=18, pady=4)
        self.canvas = tk.Canvas(list_wrap, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_wrap, orient="vertical", command=self.canvas.yview)
        self.rows_frame = tk.Frame(self.canvas, bg=BG)
        self.rows_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0,0), window=self.rows_frame, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        footer = tk.Frame(self, bg=BG)
        footer.pack(fill="x", padx=18, pady=(8,16))
        self.process_btn = tk.Button(footer, text="Générer les images", command=self.process_images, bg=GOLD, fg="white", activebackground=GOLD_DARK, relief="flat", font=("Segoe UI", 13, "bold"), padx=28, pady=10)
        self.process_btn.pack(side="right")
        tk.Label(footer, text="Maximum 10 images par traitement", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side="left", pady=12)

    def update_export_label(self):
        txt = f"Export : {self.export_dir}" if self.export_dir else "Export : non défini"
        self.export_label.config(text=txt)

    def choose_export_first_launch(self):
        messagebox.showinfo(APP_NAME, "Choisissez le dossier d’export des images produits. Ce choix sera mémorisé.")
        self.choose_export_dir()

    def choose_export_dir(self):
        folder = filedialog.askdirectory(title="Choisir le dossier d’export")
        if folder:
            self.export_dir = folder
            self.cfg["export_dir"] = folder
            save_config(self.cfg)
            self.update_export_label()

    def add_images(self):
        remaining = MAX_IMAGES - len(self.rows)
        if remaining <= 0:
            messagebox.showwarning(APP_NAME, "Maximum 10 images par traitement.")
            return
        files = filedialog.askopenfilenames(title="Ajouter des images", filetypes=[("Images", "*.jpg *.jpeg *.png")])
        for f in files[:remaining]:
            row = ImageRow(self.rows_frame, Path(f), len(self.rows))
            row.frame.pack(fill="x", pady=4)
            self.rows.append(row)
        if len(files) > remaining:
            messagebox.showwarning(APP_NAME, "Seules les 10 premières images ont été ajoutées.")

    def clear_images(self):
        for r in self.rows:
            r.frame.destroy()
        self.rows.clear()

    def process_one(self, path: Path, out_path: Path, dimension: int):
        original_size = path.stat().st_size
        target_size = 300 * 1024 if dimension == 800 else 650 * 1024
        min_quality = 88
        max_quality = 94
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im)
            if im.size[0] != im.size[1]:
                raise ValueError(f"Image non carrée : {path.name}")
            if im.mode in ("RGBA", "LA", "P"):
                bg = Image.new("RGB", im.size, "white")
                if im.mode == "P":
                    im = im.convert("RGBA")
                bg.paste(im, mask=im.split()[-1] if im.mode in ("RGBA", "LA") else None)
                im = bg
            else:
                im = im.convert("RGB")
            im = im.resize((dimension, dimension), Image.Resampling.LANCZOS)
            im = im.filter(ImageFilter.UnsharpMask(radius=1.0, percent=75, threshold=3))

            best_data = None
            for q in range(max_quality, min_quality - 1, -1):
                buf = BytesIO()
                im.save(buf, format="JPEG", quality=q, optimize=True, progressive=True)
                data = buf.getvalue()
                best_data = data
                if len(data) <= target_size:
                    break
            out_path.write_bytes(best_data)
            return original_size, len(best_data)

    def process_images(self):
        if not self.rows:
            messagebox.showwarning(APP_NAME, "Ajoutez au moins une image.")
            return
        if not self.export_dir or not Path(self.export_dir).exists():
            self.choose_export_dir()
            if not self.export_dir:
                return
        invalid = [r for r in self.rows if not r.valid]
        if invalid:
            messagebox.showerror(APP_NAME, "Certaines images sont refusées. Corrigez la sélection avant de générer.")
            return
        dimension = 800 if self.mode.get() == "prestashop" else 1200
        export = Path(self.export_dir)
        outputs = []
        try:
            for r in self.rows:
                filename = validate_final_name(r.entry.get())
                out_path = export / filename
                if out_path.exists():
                    messagebox.showerror(APP_NAME, f"Ce nom de fichier existe déjà :\n{filename}")
                    return
                outputs.append((r.path, out_path))
        except ValueError as e:
            messagebox.showerror(APP_NAME, str(e))
            return

        total_before = 0
        total_after = 0
        ok = 0
        try:
            self.process_btn.config(state="disabled", text="Optimisation en cours…")
            self.update_idletasks()
            for src, dst in outputs:
                before, after = self.process_one(src, dst, dimension)
                total_before += before
                total_after += after
                ok += 1
        except Exception as e:
            messagebox.showerror(APP_NAME, f"Impossible de traiter une image.\n\n{e}")
            return
        finally:
            self.process_btn.config(state="normal", text="Générer les images")

        reduction = 0 if total_before == 0 else (1 - total_after / total_before) * 100
        messagebox.showinfo(APP_NAME, f"{ok} image(s) générée(s) avec succès.\n\nPoids d’origine : {human_size(total_before)}\nPoids final : {human_size(total_after)}\nRéduction : {reduction:.1f} %\n\nDossier : {self.export_dir}")
        try:
            os.startfile(str(export))
        except Exception:
            pass


if __name__ == "__main__":
    app = ShopPicApp()
    app.mainloop()
