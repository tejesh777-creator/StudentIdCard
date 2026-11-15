"""Save cards as PNG or PDF (Pillow only, no extra libraries)."""
import os
import re

from backend.card_renderer import render_card


def _safe(name):
    return re.sub(r"[^A-Za-z0-9_-]", "_", name)


def export_png(student, settings, base_dir, folder):
    """Writes <reg>_front.png and <reg>_back.png; returns both paths."""
    os.makedirs(folder, exist_ok=True)
    front, back = render_card(student, settings, base_dir)
    base = _safe(student["reg_no"])
    paths = [os.path.join(folder, f"{base}_front.png"), os.path.join(folder, f"{base}_back.png")]
    front.save(paths[0], dpi=(300, 300))
    back.save(paths[1], dpi=(300, 300))
    return paths


def export_pdf(students, settings, base_dir, path, progress=None):
    """One PDF; every student gets two pages (front, back). Returns number of students."""
    if not students:
        raise ValueError("No students to export.")
    pages = []
    for i, student in enumerate(students, start=1):
        pages.extend(render_card(student, settings, base_dir))
        if progress:
            progress(i, len(students))
    pages[0].save(path, "PDF", resolution=300, save_all=True, append_images=pages[1:])
    return len(students)


def export_bulk_png(students, settings, base_dir, folder, progress=None):
    for i, student in enumerate(students, start=1):
        export_png(student, settings, base_dir, folder)
        if progress:
            progress(i, len(students))
    return len(students)
