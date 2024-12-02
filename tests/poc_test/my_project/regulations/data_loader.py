# regulations/data_loader.py

import os
from PyPDF2 import PdfReader
from .models import Regulation


def pdf_to_text(file_path):
    text = ""
    with open(file_path, "rb") as f:
        reader = PdfReader(f)
        for page in reader.pages:
            text += page.extract_text()
    return text


def save_regulation(title, content):
    regulation = Regulation(title=title, content=content)
    regulation.save()
