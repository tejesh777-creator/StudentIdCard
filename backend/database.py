"""SQLite storage for students and card settings, plus photo copying."""
import os
import re
import shutil
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "idcards.db")
PHOTO_DIR = os.path.join(BASE_DIR, "photos")

FIELDS = ["reg_no", "name", "department", "course", "year", "dob", "blood_group",
          "phone", "emergency_phone", "address", "valid_upto", "photo_path"]

DEFAULT_SETTINGS = {
    "college_name": "ABC INSTITUTE OF TECHNOLOGY",
    "college_address": "123 College Road, City - 600001",
    "college_phone": "044-12345678",
    "accent_color": "#1f3a8a",
}


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reg_no TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                course TEXT DEFAULT '',
                year TEXT DEFAULT '',
                dob TEXT DEFAULT '',
                blood_group TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                emergency_phone TEXT DEFAULT '',
                address TEXT DEFAULT '',
                valid_upto TEXT DEFAULT '',
                photo_path TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
            """
        )


# ---------- settings ----------
def get_settings():
    settings = dict(DEFAULT_SETTINGS)
    with get_conn() as conn:
        for row in conn.execute("SELECT key, value FROM settings"):
            settings[row["key"]] = row["value"]
    return settings


def save_settings(values):
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", values.get("accent_color", "")):
        raise ValueError("Accent colour must look like #1f3a8a.")
    if not values.get("college_name", "").strip():
        raise ValueError("College name is required.")
    with get_conn() as conn:
        for k, v in values.items():
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, v.strip()))


# ---------- students ----------
def _clean(data):
    clean = {f: str(data.get(f, "") or "").strip() for f in FIELDS}
    if not clean["reg_no"] or not clean["name"] or not clean["department"]:
        raise ValueError("Register number, name and department are required.")
    if clean["dob"]:
        try:
            datetime.strptime(clean["dob"], "%d-%m-%Y")
        except ValueError:
            raise ValueError("Date of birth must be in DD-MM-YYYY format.")
    for key, label in (("phone", "Phone"), ("emergency_phone", "Emergency phone")):
        if clean[key] and not re.fullmatch(r"\+?\d[\d\s-]{7,14}", clean[key]):
            raise ValueError(f"{label} number looks invalid.")
    return clean


def add_student(data):
    clean = _clean(data)
    try:
        with get_conn() as conn:
            cur = conn.execute(
                f"INSERT INTO students ({','.join(FIELDS)}) VALUES ({','.join('?' * len(FIELDS))})",
                [clean[f] for f in FIELDS])
            return cur.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError(f"Register number {clean['reg_no']} already exists.")


def update_student(student_id, data):
    clean = _clean(data)
    try:
        with get_conn() as conn:
            conn.execute(
                f"UPDATE students SET {','.join(f + '=?' for f in FIELDS)} WHERE id=?",
                [clean[f] for f in FIELDS] + [student_id])
    except sqlite3.IntegrityError:
        raise ValueError(f"Register number {clean['reg_no']} already exists.")


def get_students(search="", department="All"):
    like = f"%{search.strip()}%"
    sql = "SELECT * FROM students WHERE (reg_no LIKE ? OR name LIKE ? OR department LIKE ?)"
    args = [like, like, like]
    if department and department != "All":
        sql += " AND department = ?"
        args.append(department)
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql + " ORDER BY reg_no", args)]


def get_student(student_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
    return dict(row) if row else None


def delete_student(student_id):
    student = get_student(student_id)
    with get_conn() as conn:
        conn.execute("DELETE FROM students WHERE id=?", (student_id,))
    if student and student["photo_path"]:
        try:
            os.remove(os.path.join(BASE_DIR, student["photo_path"]))
        except OSError:
            pass


def departments():
    with get_conn() as conn:
        return [r[0] for r in conn.execute("SELECT DISTINCT department FROM students ORDER BY department")]


def save_photo(source_path, reg_no):
    """Copy a chosen photo into the project's photos/ folder; returns the relative path to store."""
    os.makedirs(PHOTO_DIR, exist_ok=True)
    ext = os.path.splitext(source_path)[1].lower() or ".jpg"
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", reg_no)
    dest = os.path.join(PHOTO_DIR, f"{safe}{ext}")
    if os.path.abspath(source_path) != os.path.abspath(dest):
        shutil.copyfile(source_path, dest)
    return os.path.relpath(dest, BASE_DIR)
