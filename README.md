<<<<<<< HEAD
# Student ID Card Generator
A Python Tkinter desktop app that creates printable student ID cards (front + back).

## Features
- Add / edit / search / delete students (with photo, blood group, DOB, phones, address)
- Live preview of the card front and back
- Export a single card as PNG or PDF
- Bulk export: all students (or one department) as one PDF or as PNG files
- Settings: college name, address, phone and card colour
- Dashboard with student and photo statistics

## Run
```
pip install -r requirements.txt      # installs pillow
python main.py
```
Database: SQLite (`idcards.db`, created automatically). Photos are copied into `photos/`.

## Tests
```
python -m unittest discover -s tests
```

## Structure
```
main.py                   entry point
backend/database.py       SQLite tables, validation, photo saving
backend/card_renderer.py  draws card front/back with Pillow (CR80 size, 300 dpi)
backend/exporter.py       PNG / PDF / bulk export
frontend/app.py           Tkinter UI (sidebar + 5 screens)
tests/test_cards.py       unit tests
```
=======
# StudentIdCard
>>>>>>> origin/main
