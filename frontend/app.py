"""Tkinter UI: sidebar + 5 screens (Dashboard, Students, ID Card, Bulk Export, Settings)."""
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser

from PIL import Image, ImageTk, ImageOps

from backend import database as db
from backend.card_renderer import render_card
from backend.exporter import export_png, export_pdf, export_bulk_png

BG = "#f4f6fb"
SIDEBAR = "#1f2a44"
SIDEBAR_HOVER = "#2e3d63"
ACCENT = "#3b6cf6"
TEXT = "#1c2333"
MUTED = "#6b7388"
FONT = ("Segoe UI", 10)
TITLE_FONT = ("Segoe UI", 18, "bold")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        db.init_db()
        self.title("Student ID Card Generator")
        self.geometry("1200x720")
        self.minsize(1050, 640)
        self.configure(bg=BG)
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview", rowheight=26, font=FONT, background="white", fieldbackground="white")
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#e4e8f2", foreground=TEXT)
        style.map("Treeview", background=[("selected", ACCENT)], foreground=[("selected", "white")])

        self.sidebar = tk.Frame(self, bg=SIDEBAR, width=210)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        tk.Label(self.sidebar, text="Student\nID Card Generator", bg=SIDEBAR, fg="white",
                 font=("Segoe UI", 15, "bold"), justify="left").pack(anchor="w", padx=20, pady=(26, 24))
        self.content = tk.Frame(self, bg=BG)
        self.content.pack(side="right", fill="both", expand=True)

        self.screens = {"Dashboard": DashboardScreen, "Students": StudentsScreen, "ID Card": CardScreen,
                        "Bulk Export": BulkScreen, "Settings": SettingsScreen}
        self.nav = {}
        for name in self.screens:
            b = tk.Label(self.sidebar, text=f"   {name}", bg=SIDEBAR, fg="white", font=("Segoe UI", 11),
                         anchor="w", padx=10, pady=11, cursor="hand2")
            b.pack(fill="x")
            b.bind("<Button-1>", lambda e, n=name: self.show(n))
            b.bind("<Enter>", lambda e, w=b: w.configure(bg=SIDEBAR_HOVER))
            b.bind("<Leave>", lambda e, w=b, n=name: w.configure(bg=ACCENT if n == self.current_name else SIDEBAR))
            self.nav[name] = b
        tk.Button(self.sidebar, text="Exit", command=self.destroy, bg="#c0392b", fg="white", relief="flat",
                  font=("Segoe UI", 10, "bold"), cursor="hand2").pack(side="bottom", fill="x", padx=20, pady=20)
        self.current = None
        self.current_name = None
        self.show("Dashboard")

    def show(self, name, **kwargs):
        if self.current is not None:
            self.current.destroy()
        self.current_name = name
        for n, b in self.nav.items():
            b.configure(bg=ACCENT if n == name else SIDEBAR)
        self.current = self.screens[name](self.content, self, **kwargs)
        self.current.pack(fill="both", expand=True, padx=28, pady=22)


class Screen(tk.Frame):
    title = ""

    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        tk.Label(self, text=self.title, bg=BG, fg=TEXT, font=TITLE_FONT).pack(anchor="w", pady=(0, 14))


def card(parent):
    return tk.Frame(parent, bg="white", highlightbackground="#dfe3ee", highlightthickness=1)


def button(parent, text, command, color=ACCENT, **kw):
    return tk.Button(parent, text=text, command=command, bg=color, fg="white", relief="flat",
                     font=("Segoe UI", 10, "bold"), padx=16, pady=7, cursor="hand2", **kw)


def make_table(parent, columns, widths, height=10):
    frame = tk.Frame(parent, bg=BG)
    tree = ttk.Treeview(frame, columns=columns, show="headings", height=height)
    for col, w in zip(columns, widths):
        tree.heading(col, text=col)
        tree.column(col, width=w, anchor="center")
    scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    return frame, tree


def student_label(s):
    return f"{s['reg_no']} - {s['name']}"


# ---------------- Dashboard ----------------
class DashboardScreen(Screen):
    title = "Dashboard"

    def __init__(self, parent, app):
        super().__init__(parent, app)
        students = db.get_students()
        with_photo = sum(1 for s in students if s["photo_path"])
        stats = [("Total Students", len(students), ACCENT), ("With Photo", with_photo, "#27ae60"),
                 ("Missing Photo", len(students) - with_photo, "#e67e22"), ("Departments", len(db.departments()), "#8e44ad")]
        row = tk.Frame(self, bg=BG)
        row.pack(fill="x")
        for label, value, color in stats:
            c = card(row)
            c.pack(side="left", expand=True, fill="x", padx=(0, 14))
            tk.Frame(c, bg=color, height=4).pack(fill="x")
            tk.Label(c, text=str(value), bg="white", fg=TEXT, font=("Segoe UI", 24, "bold")).pack(pady=(12, 0))
            tk.Label(c, text=label, bg="white", fg=MUTED, font=FONT).pack(pady=(0, 12))

        tk.Label(self, text="Recently added", bg=BG, fg=TEXT, font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(22, 6))
        frame, tree = make_table(self, ["Reg No", "Name", "Department", "Photo"], [140, 260, 180, 90], height=8)
        frame.pack(fill="both", expand=True)
        for s in sorted(students, key=lambda x: -x["id"])[:8]:
            tree.insert("", "end", values=(s["reg_no"], s["name"], s["department"], "Yes" if s["photo_path"] else "No"))
        tk.Label(self, text="Tip: add students, then open 'ID Card' to preview and export.", bg=BG, fg=MUTED,
                 font=FONT).pack(anchor="w", pady=(10, 0))


# ---------------- Students ----------------
class StudentsScreen(Screen):
    title = "Students"
    TEXT_FIELDS = [("Register No", "reg_no"), ("Name", "name"), ("Department", "department"),
                   ("Course", "course"), ("DOB (DD-MM-YYYY)", "dob"), ("Phone", "phone"),
                   ("Emergency Phone", "emergency_phone"), ("Valid Upto", "valid_upto")]

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.editing_id = None
        self.photo_source = ""   # newly chosen file
        self.photo_saved = ""    # already stored relative path
        self.thumb = None

        form = card(self)
        form.pack(fill="x")
        self.vars = {}
        for i, (label, key) in enumerate(self.TEXT_FIELDS):
            r, c = divmod(i, 3)
            tk.Label(form, text=label, bg="white", fg=MUTED, font=FONT).grid(row=r, column=c * 2, sticky="w", padx=(14, 6), pady=7)
            var = tk.StringVar()
            ttk.Entry(form, textvariable=var, width=19, font=FONT).grid(row=r, column=c * 2 + 1, padx=(0, 10), pady=7)
            self.vars[key] = var
        tk.Label(form, text="Year", bg="white", fg=MUTED, font=FONT).grid(row=2, column=4, sticky="w", padx=(14, 6))
        self.vars["year"] = tk.StringVar()
        ttk.Combobox(form, textvariable=self.vars["year"], values=["1", "2", "3", "4", "5"], width=17, state="readonly").grid(row=2, column=5, padx=(0, 10))
        tk.Label(form, text="Blood Group", bg="white", fg=MUTED, font=FONT).grid(row=3, column=0, sticky="w", padx=(14, 6), pady=7)
        self.vars["blood_group"] = tk.StringVar()
        ttk.Combobox(form, textvariable=self.vars["blood_group"], values=["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
                     width=17, state="readonly").grid(row=3, column=1, padx=(0, 10))
        tk.Label(form, text="Address", bg="white", fg=MUTED, font=FONT).grid(row=3, column=2, sticky="w", padx=(14, 6))
        self.vars["address"] = tk.StringVar()
        ttk.Entry(form, textvariable=self.vars["address"], width=52, font=FONT).grid(row=3, column=3, columnspan=3, sticky="w", padx=(0, 10))

        # photo box
        box = tk.Frame(form, bg="white")
        box.grid(row=0, column=6, rowspan=4, padx=14, pady=8)
        self.photo_label = tk.Label(box, bg="#e3e7ef", width=14, height=7, text="No photo", fg=MUTED)
        self.photo_label.pack()
        button(box, "Choose Photo", self.choose_photo, "#555e78").pack(pady=(8, 0), fill="x")

        btns = tk.Frame(self, bg=BG)
        btns.pack(fill="x", pady=12)
        self.save_btn = button(btns, "Save Student", self.save)
        self.save_btn.pack(side="left")
        button(btns, "Clear Form", self.clear, "#555e78").pack(side="left", padx=10)
        button(btns, "Delete Selected", self.delete, "#c0392b").pack(side="right")
        button(btns, "Edit Selected", self.edit_selected, "#27ae60").pack(side="right", padx=10)
        tk.Label(btns, text="Search", bg=BG, fg=MUTED, font=FONT).pack(side="left", padx=(30, 6))
        self.search = ttk.Entry(btns, width=24, font=FONT)
        self.search.pack(side="left")
        self.search.bind("<KeyRelease>", lambda e: self.refresh())

        frame, self.tree = make_table(self, ["ID", "Reg No", "Name", "Department", "Course", "Year", "Phone", "Photo"],
                                      [45, 120, 200, 150, 110, 60, 120, 70], height=9)
        frame.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda e: self.edit_selected())
        self.refresh()

    # --- photo ---
    def choose_photo(self):
        path = filedialog.askopenfilename(title="Choose student photo",
                                          filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.webp")])
        if path:
            self.photo_source = path
            self.show_thumb(path)

    def show_thumb(self, path):
        try:
            with Image.open(path) as img:
                img = ImageOps.fit(ImageOps.exif_transpose(img).convert("RGB"), (110, 140), Image.LANCZOS, centering=(0.5, 0.35))
            self.thumb = ImageTk.PhotoImage(img)
            self.photo_label.configure(image=self.thumb, text="", width=110, height=140)
        except Exception:
            messagebox.showerror("Photo", "Could not open that image.")
            self.photo_source = ""

    def reset_thumb(self):
        self.thumb = None
        self.photo_label.configure(image="", text="No photo", width=14, height=7)

    # --- form actions ---
    def collect(self):
        data = {k: v.get() for k, v in self.vars.items()}
        data["photo_path"] = self.photo_saved
        return data

    def save(self):
        data = self.collect()
        try:
            if self.photo_source and data["reg_no"].strip():
                data["photo_path"] = db.save_photo(self.photo_source, data["reg_no"].strip())
            if self.editing_id:
                db.update_student(self.editing_id, data)
            else:
                db.add_student(data)
        except (ValueError, OSError) as e:
            messagebox.showerror("Cannot save", str(e))
            return
        messagebox.showinfo("Saved", "Student updated." if self.editing_id else "Student added.")
        self.clear()
        self.refresh()

    def clear(self):
        for v in self.vars.values():
            v.set("")
        self.editing_id = None
        self.photo_source = ""
        self.photo_saved = ""
        self.reset_thumb()
        self.save_btn.configure(text="Save Student")

    def selected_id(self):
        sel = self.tree.selection()
        return self.tree.item(sel[0])["values"][0] if sel else None

    def edit_selected(self):
        sid = self.selected_id()
        if sid is None:
            messagebox.showinfo("Edit", "Select a student in the table first.")
            return
        s = db.get_student(sid)
        self.clear()
        self.editing_id = sid
        for k, v in self.vars.items():
            v.set(s.get(k, ""))
        self.photo_saved = s["photo_path"]
        full = os.path.join(db.BASE_DIR, s["photo_path"]) if s["photo_path"] else ""
        if full and os.path.isfile(full):
            self.show_thumb(full)
        self.save_btn.configure(text="Update Student")

    def delete(self):
        sid = self.selected_id()
        if sid is None:
            messagebox.showinfo("Delete", "Select a student first.")
            return
        if messagebox.askyesno("Confirm", "Delete this student and their photo?"):
            db.delete_student(sid)
            if self.editing_id == sid:
                self.clear()
            self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for s in db.get_students(self.search.get()):
            self.tree.insert("", "end", values=(s["id"], s["reg_no"], s["name"], s["department"], s["course"],
                                                s["year"], s["phone"], "Yes" if s["photo_path"] else "No"))


# ---------------- ID Card preview / export ----------------
class CardScreen(Screen):
    title = "ID Card"
    PREVIEW_W = 440

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.students = db.get_students()
        self.images = []
        self.rendered = None

        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x")
        tk.Label(bar, text="Student", bg=BG, fg=MUTED, font=FONT).pack(side="left")
        self.combo = ttk.Combobox(bar, values=[student_label(s) for s in self.students], width=40, state="readonly")
        self.combo.pack(side="left", padx=10)
        self.combo.bind("<<ComboboxSelected>>", lambda e: self.preview())
        button(bar, "Export PNG", self.export_png, "#27ae60").pack(side="right")
        button(bar, "Export PDF", self.export_pdf).pack(side="right", padx=10)

        self.stage = tk.Frame(self, bg=BG)
        self.stage.pack(fill="both", expand=True, pady=18)
        self.msg = tk.Label(self.stage, bg=BG, fg=MUTED, font=("Segoe UI", 12),
                            text="Select a student to preview the front and back of the card." if self.students
                            else "No students yet. Add one in the Students screen first.")
        self.msg.pack(pady=60)

    def current(self):
        i = self.combo.current()
        return self.students[i] if i >= 0 else None

    def preview(self):
        s = self.current()
        if not s:
            return
        for w in self.stage.winfo_children():
            w.destroy()
        self.images = []
        self.rendered = render_card(s, db.get_settings(), db.BASE_DIR)
        for title, img in zip(("Front", "Back"), self.rendered):
            h = int(self.PREVIEW_W * img.height / img.width)
            self.images.append(ImageTk.PhotoImage(img.resize((self.PREVIEW_W, h), Image.LANCZOS)))
            col = tk.Frame(self.stage, bg=BG)
            col.pack(side="left", expand=True)
            tk.Label(col, text=title, bg=BG, fg=MUTED, font=("Segoe UI", 11, "bold")).pack(pady=(0, 6))
            tk.Label(col, image=self.images[-1], bd=1, relief="solid").pack()

    def export_png(self):
        s = self.current()
        if not s:
            messagebox.showinfo("Export", "Select a student first.")
            return
        folder = filedialog.askdirectory(title="Choose folder to save the PNG files")
        if folder:
            paths = export_png(s, db.get_settings(), db.BASE_DIR, folder)
            messagebox.showinfo("Exported", "Saved:\n" + "\n".join(paths))

    def export_pdf(self):
        s = self.current()
        if not s:
            messagebox.showinfo("Export", "Select a student first.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=f"{s['reg_no']}_IDCard.pdf",
                                            filetypes=[("PDF", "*.pdf")])
        if path:
            export_pdf([s], db.get_settings(), db.BASE_DIR, path)
            messagebox.showinfo("Exported", f"Saved:\n{path}")


# ---------------- Bulk export ----------------
class BulkScreen(Screen):
    title = "Bulk Export"

    def __init__(self, parent, app):
        super().__init__(parent, app)
        box = card(self)
        box.pack(fill="x")
        tk.Label(box, text="Generate ID cards for many students at once", bg="white", fg=TEXT,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(18, 4))
        tk.Label(box, text="Choose a department (or All). The PDF has the front and back page for every student.",
                 bg="white", fg=MUTED, font=FONT).pack(anchor="w", padx=20)
        row = tk.Frame(box, bg="white")
        row.pack(anchor="w", padx=20, pady=16)
        tk.Label(row, text="Department", bg="white", fg=MUTED, font=FONT).pack(side="left")
        self.dept = ttk.Combobox(row, values=["All"] + db.departments(), width=26, state="readonly")
        self.dept.set("All")
        self.dept.pack(side="left", padx=10)
        self.dept.bind("<<ComboboxSelected>>", lambda e: self.update_count())
        self.count = tk.Label(row, bg="white", fg=ACCENT, font=("Segoe UI", 10, "bold"))
        self.count.pack(side="left", padx=10)
        btns = tk.Frame(box, bg="white")
        btns.pack(anchor="w", padx=20, pady=(0, 18))
        button(btns, "Export All as PDF", self.bulk_pdf).pack(side="left")
        button(btns, "Export All as PNG Files", self.bulk_png, "#27ae60").pack(side="left", padx=12)
        self.progress = ttk.Progressbar(self, length=420)
        self.progress.pack(anchor="w", pady=(16, 4))
        self.status = tk.Label(self, bg=BG, fg=MUTED, font=FONT)
        self.status.pack(anchor="w")
        self.update_count()

    def students(self):
        return db.get_students(department=self.dept.get())

    def update_count(self):
        self.count.configure(text=f"{len(self.students())} student(s)")

    def on_progress(self, done, total):
        self.progress.configure(maximum=total, value=done)
        self.status.configure(text=f"Generated {done} of {total}")
        self.update_idletasks()

    def bulk_pdf(self):
        students = self.students()
        if not students:
            messagebox.showinfo("Export", "No students to export.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile="All_IDCards.pdf", filetypes=[("PDF", "*.pdf")])
        if path:
            n = export_pdf(students, db.get_settings(), db.BASE_DIR, path, self.on_progress)
            messagebox.showinfo("Exported", f"{n} card(s) saved to:\n{path}")

    def bulk_png(self):
        students = self.students()
        if not students:
            messagebox.showinfo("Export", "No students to export.")
            return
        folder = filedialog.askdirectory(title="Choose folder for the PNG files")
        if folder:
            n = export_bulk_png(students, db.get_settings(), db.BASE_DIR, folder, self.on_progress)
            messagebox.showinfo("Exported", f"{n} card(s) saved in:\n{folder}")


# ---------------- Settings ----------------
class SettingsScreen(Screen):
    title = "Settings"

    def __init__(self, parent, app):
        super().__init__(parent, app)
        s = db.get_settings()
        box = card(self)
        box.pack(fill="x")
        self.vars = {}
        for i, (label, key) in enumerate([("College name", "college_name"), ("College address", "college_address"),
                                          ("College phone", "college_phone"), ("Accent colour", "accent_color")]):
            tk.Label(box, text=label, bg="white", fg=MUTED, font=FONT).grid(row=i, column=0, sticky="w", padx=(20, 10), pady=10)
            var = tk.StringVar(value=s[key])
            ttk.Entry(box, textvariable=var, width=52, font=FONT).grid(row=i, column=1, sticky="w", pady=10)
            self.vars[key] = var
        self.swatch = tk.Label(box, width=4, bg=s["accent_color"])
        self.swatch.grid(row=3, column=2, padx=10)
        button(box, "Pick colour", self.pick, "#555e78").grid(row=3, column=3, padx=(0, 20))
        button(self, "Save Settings", self.save).pack(anchor="w", pady=16)
        tk.Label(self, text="These details appear on every ID card.", bg=BG, fg=MUTED, font=FONT).pack(anchor="w")

    def pick(self):
        _, hex_color = colorchooser.askcolor(color=self.vars["accent_color"].get(), title="Card accent colour")
        if hex_color:
            self.vars["accent_color"].set(hex_color)
            self.swatch.configure(bg=hex_color)

    def save(self):
        try:
            db.save_settings({k: v.get() for k, v in self.vars.items()})
        except ValueError as e:
            messagebox.showerror("Settings", str(e))
            return
        self.swatch.configure(bg=self.vars["accent_color"].get())
        messagebox.showinfo("Settings", "Saved. New cards will use these details.")


def run():
    App().mainloop()
