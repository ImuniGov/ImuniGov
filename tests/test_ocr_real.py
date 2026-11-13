import os
import shutil

import pytest
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from backend.worker import extract, parse_candidates

available = bool(shutil.which("tesseract") and shutil.which("pdftoppm"))
pytestmark = pytest.mark.skipif(
    not available and not os.environ.get("REQUIRE_OCR"),
    reason="Tesseract/Poppler required; executed in Docker CI.",
)


def card():
    image = Image.new("RGB", (1400, 500), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("DejaVuSans.ttf", 46)
    draw.text((70, 70), "EXEMPLO SINTETICO - IMUNIGUIA", font=font, fill="black")
    draw.text((70, 210), "BCG dose 1 02/01/2026", font=font, fill="black")
    return image


@pytest.mark.parametrize("extension", ["png", "pdf"])
def test_real_tesseract_reads_image_and_scanned_pdf(tmp_path, extension):
    assert available, "OCR dependencies must be installed in the test container."
    path = tmp_path / ("synthetic." + extension)
    card().save(path, resolution=120)
    text, confidence = extract(path)
    candidates = parse_candidates(text, confidence)
    assert candidates and candidates[0]["vaccine"] == "BCG" and candidates[0]["dose_date"] == "2026-01-02"
    assert confidence > 0


def test_pdf_embedded_text_is_candidate_not_confirmed(tmp_path):
    writer = PdfWriter()
    page = writer.add_blank_page(width=800, height=400)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 20 Tf 50 300 Td (BCG dose 1 02/01/2026) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    path = tmp_path / "embedded.pdf"
    writer.write(path)
    text, confidence = extract(path)
    assert parse_candidates(text)[0]["vaccine"] == "BCG" and confidence == 0
