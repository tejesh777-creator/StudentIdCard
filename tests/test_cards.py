import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image

from backend import database as db
from backend.card_renderer import render_card, W, H
from backend.exporter import export_png, export_pdf


class CardTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        db.BASE_DIR = self.dir
        db.DB_PATH = os.path.join(self.dir, "t.db")
        db.PHOTO_DIR = os.path.join(self.dir, "photos")
        db.init_db()
        self.photo_src = os.path.join(self.dir, "src.jpg")
        Image.new("RGB", (400, 500), "#556677").save(self.photo_src)

    def tearDown(self):
        shutil.rmtree(self.dir)

    def student(self, **kw):
        data = {"reg_no": "RA2111001", "name": "Asha Raman", "department": "CSE", "course": "B.Tech", "year": "3",
                "dob": "12-05-2004", "blood_group": "O+", "phone": "9876543210", "emergency_phone": "9123456780",
                "address": "12 Park Street, Chennai 600001", "valid_upto": "2027"}
        data.update(kw)
        return data

    def test_add_validation(self):
        db.add_student(self.student())
        with self.assertRaises(ValueError):
            db.add_student(self.student())                       # duplicate reg no
        with self.assertRaises(ValueError):
            db.add_student(self.student(reg_no="X", dob="2004-05-12"))   # wrong date format
        with self.assertRaises(ValueError):
            db.add_student(self.student(reg_no="Y", phone="abc"))
        with self.assertRaises(ValueError):
            db.add_student(self.student(reg_no="", name=""))

    def test_update_and_delete_removes_photo(self):
        photo = db.save_photo(self.photo_src, "RA2111001")
        sid = db.add_student(self.student(photo_path=photo))
        self.assertTrue(os.path.isfile(os.path.join(self.dir, photo)))
        db.update_student(sid, self.student(name="Asha R", photo_path=photo))
        self.assertEqual(db.get_student(sid)["name"], "Asha R")
        db.delete_student(sid)
        self.assertFalse(os.path.isfile(os.path.join(self.dir, photo)))

    def test_render_sizes_with_and_without_photo(self):
        settings = db.get_settings()
        for photo in ("", db.save_photo(self.photo_src, "RA2111001")):
            front, back = render_card(self.student(photo_path=photo), settings, self.dir)
            self.assertEqual(front.size, (W, H))
            self.assertEqual(back.size, (W, H))

    def test_long_text_does_not_crash(self):
        s = self.student(name="Venkata Subramanian Ramachandran Iyer Junior", department="Electronics and Communication Engineering",
                         address="Flat 4B, Very Long Apartment Name, Some Extremely Long Street Name, Chennai, Tamil Nadu 600001 " * 2)
        render_card(s, db.get_settings(), self.dir)

    def test_exports(self):
        a = self.student()
        b = self.student(reg_no="RA2111002", name="Ravi")
        out = os.path.join(self.dir, "out")
        paths = export_png(a, db.get_settings(), self.dir, out)
        self.assertTrue(all(os.path.isfile(p) for p in paths))
        pdf = os.path.join(self.dir, "cards.pdf")
        self.assertEqual(export_pdf([a, b], db.get_settings(), self.dir, pdf), 2)
        self.assertGreater(os.path.getsize(pdf), 1000)
        self.assertTrue(open(pdf, "rb").read(5) == b"%PDF-")

    def test_settings_validation(self):
        with self.assertRaises(ValueError):
            db.save_settings({"college_name": "X", "accent_color": "blue"})
        db.save_settings({"college_name": "SRM", "accent_color": "#112233"})
        self.assertEqual(db.get_settings()["college_name"], "SRM")


if __name__ == "__main__":
    unittest.main()
