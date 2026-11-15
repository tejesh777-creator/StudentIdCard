"""Draws the front and back of a student ID card with Pillow (CR80 size, 300 dpi)."""
import os
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont, ImageOps

W, H = 1012, 638  # 3.375 x 2.125 inch at 300 dpi
TEXT = "#1c2333"
MUTED = "#5c6577"
WHITE = "#ffffff"

_REGULAR = ["arial.ttf", "segoeui.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf", "Helvetica.ttc"]
_BOLD = ["arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "Helvetica.ttc"]


@lru_cache(maxsize=None)
def font(size, bold=False):
    for name in (_BOLD if bold else _REGULAR):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def _fit(draw, text, max_width, start, minimum, bold=False):
    """Largest font (start..minimum) in which text fits max_width."""
    size = start
    while size > minimum and draw.textlength(text, font=font(size, bold)) > max_width:
        size -= 2
    return font(size, bold)


def _wrap(draw, text, fnt, max_width):
    lines = []
    for paragraph in (text or "").splitlines() or [""]:
        line = ""
        for word in paragraph.split():
            trial = f"{line} {word}".strip()
            if draw.textlength(trial, font=fnt) <= max_width:
                line = trial
            else:
                if line:
                    lines.append(line)
                line = word
        lines.append(line)
    return lines


def _photo(student, size, base_dir, accent):
    """Student photo cropped to size, or a placeholder with the initial."""
    path = os.path.join(base_dir, student.get("photo_path") or "")
    if student.get("photo_path") and os.path.isfile(path):
        try:
            with Image.open(path) as img:
                img = ImageOps.exif_transpose(img).convert("RGB")
                return ImageOps.fit(img, size, Image.LANCZOS, centering=(0.5, 0.35))
        except Exception:
            pass
    placeholder = Image.new("RGB", size, "#e3e7ef")
    d = ImageDraw.Draw(placeholder)
    initial = (student.get("name") or "?").strip()[:1].upper()
    d.text((size[0] / 2, size[1] / 2), initial, font=font(110, True), fill=accent, anchor="mm")
    return placeholder


def render_front(student, settings, base_dir):
    accent = settings["accent_color"]
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)

    # header
    d.rectangle([0, 0, W, 128], fill=accent)
    d.text((W / 2, 52), settings["college_name"].upper(),
           font=_fit(d, settings["college_name"].upper(), W - 60, 40, 22, True), fill=WHITE, anchor="mm")
    d.text((W / 2, 98), "STUDENT IDENTITY CARD", font=font(22, True), fill="#cfd8f5", anchor="mm")

    # photo with border
    px, py, pw, ph = 40, 160, 236, 300
    d.rectangle([px - 5, py - 5, px + pw + 4, py + ph + 4], fill=accent)
    img.paste(_photo(student, (pw, ph), base_dir, accent), (px, py))

    # name
    name = student["name"].upper()
    d.text((310, 160), name, font=_fit(d, name, W - 340, 40, 24, True), fill=accent)
    d.line([310, 212, W - 30, 212], fill="#d5dae6", width=2)

    # details
    course = student.get("course", "")
    if student.get("year"):
        course = f"{course} - Year {student['year']}".strip(" -")
    rows = [("Reg No", student["reg_no"]), ("Department", student["department"]), ("Course", course),
            ("DOB", student.get("dob", "")), ("Blood Group", student.get("blood_group", ""))]
    y = 232
    for label, value in rows:
        d.text((310, y), label, font=font(23), fill=MUTED)
        d.text((500, y - 2), ":", font=font(26, True), fill=MUTED)
        d.text((520, y - 3), value or "-", font=_fit(d, value or "-", W - 550, 27, 17, True), fill=TEXT)
        y += 52

    # footer
    d.rectangle([0, H - 62, W, H], fill=accent)
    d.text((40, H - 31), f"Valid Upto: {student.get('valid_upto') or '-'}", font=font(26, True), fill=WHITE, anchor="lm")
    d.text((W - 40, H - 31), "Carry this card at all times", font=font(20), fill="#cfd8f5", anchor="rm")
    return img


def render_back(student, settings, base_dir):
    accent = settings["accent_color"]
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)

    d.rectangle([0, 0, W, 86], fill=accent)
    d.text((W / 2, 43), settings["college_name"].upper(),
           font=_fit(d, settings["college_name"].upper(), W - 60, 32, 20, True), fill=WHITE, anchor="mm")

    y = 118
    d.text((40, y), "If found, please return to:", font=font(24, True), fill=accent)
    y += 40
    for line in _wrap(d, settings["college_address"], font(23), W - 80):
        d.text((40, y), line, font=font(23), fill=TEXT)
        y += 30
    if settings.get("college_phone"):
        d.text((40, y), f"Phone: {settings['college_phone']}", font=font(23), fill=TEXT)
        y += 30

    y += 14
    d.line([40, y, W - 40, y], fill="#d5dae6", width=2)
    y += 22
    for label, value in (("Student Phone", student.get("phone", "")),
                         ("Emergency Contact", student.get("emergency_phone", ""))):
        d.text((40, y), f"{label}:", font=font(22), fill=MUTED)
        d.text((290, y), value or "-", font=font(23, True), fill=TEXT)
        y += 38
    d.text((40, y), "Address:", font=font(22), fill=MUTED)
    ay = y
    for line in _wrap(d, student.get("address", "") or "-", font(22, True), W - 330)[:3]:
        d.text((290, ay), line, font=font(22, True), fill=TEXT)
        ay += 30

    # signature
    d.line([W - 340, H - 110, W - 40, H - 110], fill=TEXT, width=2)
    d.text((W - 190, H - 88), "Authorised Signatory", font=font(20), fill=MUTED, anchor="mm")

    d.rectangle([0, H - 40, W, H], fill=accent)
    d.text((W / 2, H - 20), "This card is the property of the institution and is non-transferable.",
           font=font(18), fill="#cfd8f5", anchor="mm")
    return img


def render_card(student, settings, base_dir):
    """Returns (front, back) PIL images."""
    return render_front(student, settings, base_dir), render_back(student, settings, base_dir)
