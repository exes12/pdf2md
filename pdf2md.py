import os
from pathlib import Path
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import pymupdf4llm

# --- Color Palettes for Light & Dark Mode ---
THEMES = {
    "dark": {
        "bg": "#1e1e24",
        "fg": "#f0f0f5",
        "muted": "#9e9ea8",
        "entry_bg": "#2b2b36",
        "entry_fg": "#ffffff",
        "disabled_bg": "#18181d",
        "btn_bg": "#383846",
        "btn_fg": "#ffffff",
        "accent_bg": "#3a86ff",
        "accent_fg": "#ffffff",
    },
    "light": {
        "bg": "#f5f5f7",
        "fg": "#1d1d1f",
        "muted": "#6e6e73",
        "entry_bg": "#ffffff",
        "entry_fg": "#000000",
        "disabled_bg": "#e5e5ea",
        "btn_bg": "#e0e0e6",
        "btn_fg": "#1d1d1f",
        "accent_bg": "#0066cc",
        "accent_fg": "#ffffff",
    },
}


class PDFToMarkdownApp:

    def __init__(self, root):
        self.root = root
        self.root.title("PDF to Markdown Converter")
        self.root.geometry("600x430")
        self.root.resizable(False, False)

        # State Variables
        self.is_dark_mode = tk.BooleanVar(value=True)
        self.pdf_path = tk.StringVar()
        self.md_out_dir = tk.StringVar()
        self.include_images = tk.BooleanVar(value=False)
        self.img_base_dir = tk.StringVar()
        self.status_text = tk.StringVar(value="Ready. Select a PDF to begin.")
        self.subfolder_preview = tk.StringVar(value="")

        # Trace changes to update subfolder preview dynamically
        self.pdf_path.trace_add("write", self.update_preview)
        self.img_base_dir.trace_add("write", self.update_preview)

        self.build_ui()
        self.apply_theme()

    def build_ui(self):
        # Main container
        self.main_frame = tk.Frame(self.root, padx=24, pady=20)
        self.main_frame.pack(fill="both", expand=True)

        # --- Header Row (Title + Dark Mode Toggle) ---
        self.header_frame = tk.Frame(self.main_frame)
        self.header_frame.pack(fill="x", pady=(0, 18))

        self.title_lbl = tk.Label(
            self.header_frame,
            text="PDF to Markdown",
            font=("Segoe UI", 16, "bold"),
        )
        self.title_lbl.pack(side="left")

        self.theme_cb = tk.Checkbutton(
            self.header_frame,
            text="Dark Mode",
            variable=self.is_dark_mode,
            command=self.apply_theme,
            font=("Segoe UI", 10),
            bd=0,
            highlightthickness=0,
        )
        self.theme_cb.pack(side="right")

        # --- 1. PDF Input File ---
        self.lbl_pdf = tk.Label(
            self.main_frame,
            text="1. Select PDF File:",
            font=("Segoe UI", 10, "bold"),
        )
        self.lbl_pdf.pack(anchor="w")

        self.pdf_row = tk.Frame(self.main_frame)
        self.pdf_row.pack(fill="x", pady=(4, 14))

        self.ent_pdf = tk.Entry(
            self.pdf_row,
            textvariable=self.pdf_path,
            font=("Segoe UI", 10),
             relief="flat",
        )
        self.ent_pdf.pack(
            side="left", fill="x", expand=True, ipady=5, padx=(0, 8)
        )

        self.btn_pdf = tk.Button(
            self.pdf_row,
            text="Browse...",
            command=self.browse_pdf,
            relief="flat",
            padx=12,
            pady=4,
        )
        self.btn_pdf.pack(side="right")

        # --- 2. Markdown Output Folder ---
        self.lbl_md = tk.Label(
            self.main_frame,
            text="2. Markdown Output Folder:",
            font=("Segoe UI", 10, "bold"),
        )
        self.lbl_md.pack(anchor="w")

        self.md_row = tk.Frame(self.main_frame)
        self.md_row.pack(fill="x", pady=(4, 14))

        self.ent_md = tk.Entry(
            self.md_row,
            textvariable=self.md_out_dir,
            font=("Segoe UI", 10),
            relief="flat",
        )
        self.ent_md.pack(
            side="left", fill="x", expand=True, ipady=5, padx=(0, 8)
        )

        self.btn_md = tk.Button(
            self.md_row,
            text="Browse...",
            command=self.browse_md_dir,
            relief="flat",
            padx=12,
            pady=4,
        )
        self.btn_md.pack(side="right")

        # --- 3. Image Extraction Options ---
        self.cb_images = tk.Checkbutton(
            self.main_frame,
            text="Extract and include images in a folder",
            variable=self.include_images,
            command=self.toggle_image_fields,
            font=("Segoe UI", 10, "bold"),
            bd=0,
            highlightthickness=0,
        )
        self.cb_images.pack(anchor="w", pady=(2, 4))

        self.lbl_img = tk.Label(
            self.main_frame,
            text="Where to store the generated image folder:",
            font=("Segoe UI", 9),
        )
        self.lbl_img.pack(anchor="w")

        self.img_row = tk.Frame(self.main_frame)
        self.img_row.pack(fill="x", pady=(4, 2))

        self.ent_img = tk.Entry(
            self.img_row,
            textvariable=self.img_base_dir,
            font=("Segoe UI", 10),
            relief="flat",
            state="disabled",
        )
        self.ent_img.pack(
            side="left", fill="x", expand=True, ipady=5, padx=(0, 8)
        )

        self.btn_img = tk.Button(
            self.img_row,
            text="Browse...",
            command=self.browse_img_dir,
            relief="flat",
            padx=12,
            pady=4,
            state="disabled",
        )
        self.btn_img.pack(side="right")

        self.lbl_preview = tk.Label(
            self.main_frame,
            textvariable=self.subfolder_preview,
            font=("Segoe UI", 8, "italic"),
        )
        self.lbl_preview.pack(anchor="w", pady=(0, 16))

        # --- 4. Convert Button & Status ---
        self.btn_convert = tk.Button(
            self.main_frame,
            text="Convert to Markdown",
            command=self.start_conversion,
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            pady=8,
            cursor="hand2",
        )
        self.btn_convert.pack(fill="x", pady=(4, 10))

        self.lbl_status = tk.Label(
            self.main_frame,
            textvariable=self.status_text,
            font=("Segoe UI", 9),
        )
        self.lbl_status.pack(anchor="center")

    # --- UI Logic & Helpers ---
    def browse_pdf(self):
        file_path = filedialog.askopenfilename(
            title="Select PDF File", filetypes=[("PDF Files", "*.pdf")]
        )
        if file_path:
            self.pdf_path.set(file_path)
            parent_dir = str(Path(file_path).parent)
            # Auto-fill output directories if they are empty
            if not self.md_out_dir.get():
                self.md_out_dir.set(parent_dir)
            if not self.img_base_dir.get():
                self.img_base_dir.set(parent_dir)

    def browse_md_dir(self):
        folder = filedialog.askdirectory(
            title="Select Markdown Output Folder"
        )
        if folder:
            self.md_out_dir.set(folder)

    def browse_img_dir(self):
        folder = filedialog.askdirectory(
            title="Select Where to Store Image Folder"
        )
        if folder:
            self.img_base_dir.set(folder)

    def toggle_image_fields(self):
        state = "normal" if self.include_images.get() else "disabled"
        self.ent_img.config(state=state)
        self.btn_img.config(state=state)
        self.update_preview()
        self.apply_theme()

    def update_preview(self, *args):
        if not self.include_images.get():
            self.subfolder_preview.set("")
            return

        pdf = self.pdf_path.get().strip()
        base = self.img_base_dir.get().strip()
        if pdf and base:
            pdf_stem = Path(pdf).stem
            target_folder = Path(base) / f"{pdf_stem}_images"
            self.subfolder_preview.set(
                f"Auto-generating folder: {target_folder}"
            )
        else:
            self.subfolder_preview.set(
                "A folder named '<pdf_name>_images' will be created automatically."
            )

    def apply_theme(self):
        t = THEMES["dark"] if self.is_dark_mode.get() else THEMES["light"]

        self.root.config(bg=t["bg"])
        for frame in (
            self.main_frame,
            self.header_frame,
            self.pdf_row,
            self.md_row,
            self.img_row,
        ):
            frame.config(bg=t["bg"])

        for lbl in (self.title_lbl, self.lbl_pdf, self.lbl_md):
            lbl.config(bg=t["bg"], fg=t["fg"])

        for muted_lbl in (self.lbl_img, self.lbl_preview, self.lbl_status):
            muted_lbl.config(bg=t["bg"], fg=t["muted"])

        for cb in (self.theme_cb, self.cb_images):
            cb.config(
                bg=t["bg"],
                fg=t["fg"],
                selectcolor=t["entry_bg"],
                activebackground=t["bg"],
                activeforeground=t["fg"],
            )

        for ent in (self.ent_pdf, self.ent_md, self.ent_img):
            ent.config(
                bg=t["entry_bg"],
                fg=t["entry_fg"],
                insertbackground=t["fg"],
                disabledbackground=t["disabled_bg"],
                disabledforeground=t["muted"],
            )

        for btn in (self.btn_pdf, self.btn_md, self.btn_img):
            btn.config(
                bg=t["btn_bg"],
                fg=t["btn_fg"],
                activebackground=t["entry_bg"],
                activeforeground=t["fg"],
            )

        self.btn_convert.config(
            bg=t["accent_bg"],
            fg=t["accent_fg"],
            activebackground=t["accent_bg"],
            activeforeground=t["accent_fg"],
        )

    # --- Conversion Engine ---
    def start_conversion(self):
        pdf_file = self.pdf_path.get().strip()
        md_dir = self.md_out_dir.get().strip()
        extract_imgs = self.include_images.get()
        img_base = self.img_base_dir.get().strip()

        if not pdf_file or not os.path.isfile(pdf_file):
            messagebox.showwarning(
                "Missing Input", "Please select a valid PDF file."
            )
            return
        if not md_dir:
            messagebox.showwarning(
                "Missing Output", "Please specify a Markdown output folder."
            )
            return
        if extract_imgs and not img_base:
            messagebox.showwarning(
                "Missing Image Path",
                "Please specify where the image folder should be stored.",
            )
            return

        # Disable button while converting
        self.btn_convert.config(state="disabled", text="Converting...")
        self.status_text.set("Extracting content... Please wait.")

        # Run in background thread so GUI stays responsive
        threading.Thread(
            target=self.run_conversion,
            args=(pdf_file, md_dir, extract_imgs, img_base),
            daemon=True,
        ).start()

    def run_conversion(self, pdf_file, md_dir, extract_imgs, img_base):
        try:
            pdf_path_obj = Path(pdf_file)
            pdf_name = pdf_path_obj.stem

            md_dir_obj = Path(md_dir)
            md_dir_obj.mkdir(parents=True, exist_ok=True)
            md_output_file = md_dir_obj / f"{pdf_name}.md"

            if extract_imgs:
                # Automatically generate folder with the name of the PDF file
                img_target_dir = Path(img_base) / f"{pdf_name}_images"
                img_target_dir.mkdir(parents=True, exist_ok=True)
                img_path_posix = img_target_dir.resolve().as_posix()

                md_text = pymupdf4llm.to_markdown(
                    pdf_file,
                    write_images=True,
                    image_path=img_path_posix,
                    image_format="png",
                )

                # If Markdown file and Images are on the same drive, use clean relative paths
                try:
                    rel_path = Path(
                        os.path.relpath(img_target_dir.resolve(), md_dir_obj.resolve())
                    ).as_posix()
                    md_text = md_text.replace(img_path_posix, rel_path)
                except ValueError:
                    pass  # Different drives on Windows; keep absolute POSIX path
            else:
                md_text = pymupdf4llm.to_markdown(
                    pdf_file, write_images=False
                )

            # Write output Markdown file
            md_output_file.write_text(md_text, encoding="utf-8")

            self.root.after(
                0,
                lambda: self.finish_conversion(
                    True, f"Success! Saved to: {md_output_file.name}"
                ),
            )
        except Exception as e:
            self.root.after(0, lambda: self.finish_conversion(False, str(e)))

    def finish_conversion(self, success, message):
        self.btn_convert.config(state="normal", text="Convert to Markdown")
        if success:
            self.status_text.set(message)
            messagebox.showinfo("Conversion Complete", message)
        else:
            self.status_text.set("Conversion failed.")
            messagebox.showerror("Error", f"An error occurred:\n{message}")


if __name__ == "__main__":
    root = tk.Tk()
    app = PDFToMarkdownApp(root)
    root.mainloop()