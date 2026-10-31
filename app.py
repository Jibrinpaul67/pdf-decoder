
import io
import os
import re
from pathlib import Path

import fitz
import pytesseract
from PIL import Image
from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB
MAX_PAGES = 100


def needs_ocr(text):
    if not text.strip():
        return True

    replacement_count = text.count("\ufffd")
    return replacement_count / len(text) > 0.05


def extract_with_ocr(page):
    pix = page.get_pixmap(
        matrix=fitz.Matrix(3, 3),
        alpha=False
    )

    image = Image.open(io.BytesIO(pix.tobytes("png")))

    return pytesseract.image_to_string(image, lang="eng")


def decode_pdf(pdf_bytes):
    document = fitz.open(stream=pdf_bytes, filetype="pdf")

    try:
        if document.page_count > MAX_PAGES:
            raise ValueError(
                f"PDF exceeds the {MAX_PAGES}-page limit."
            )

        recovered_text = []

        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text")

            if needs_ocr(text):
                text = extract_with_ocr(page)

            recovered_text.append(
                f"--- PAGE {page_number} ---\n{text}"
            )

        return "\n\n".join(recovered_text)
    finally:
        document.close()


@app.route("/", methods=["GET", "POST"])
def index():
    error = None

    if request.method == "POST":
        uploaded_file = request.files.get("pdf")

        if not uploaded_file or not uploaded_file.filename:
            return render_template(
                "index.html",
                error="Please choose a PDF file."
            ), 400

        filename = secure_filename(uploaded_file.filename)

        if not filename.lower().endswith(".pdf"):
            return render_template(
                "index.html",
                error="Please upload a PDF file."
            ), 400

        try:
            pdf_bytes = uploaded_file.read()

            if not pdf_bytes:
                raise ValueError("The uploaded file is empty.")

            if not pdf_bytes.startswith(b"%PDF-"):
                raise ValueError(
                    "This file doesn't appear to be a valid PDF."
                )

            text = decode_pdf(pdf_bytes)

            if not text.strip():
                raise ValueError(
                    "No readable text was recovered from this PDF."
                )

            output = io.BytesIO(text.encode("utf-8"))
            output.seek(0)

            output_name = Path(filename).stem + "_decoded.txt"

            return send_file(
                output,
                mimetype="text/plain; charset=utf-8",
                as_attachment=True,
                download_name=output_name
            )

        except (ValueError, RuntimeError, fitz.FileDataError) as exc:
            error = str(exc)

        except Exception:
            app.logger.exception("PDF processing failed")
            error = (
                "We couldn't process this PDF. "
                "Try another file or a smaller PDF."
            )

    return render_template("index.html", error=error)


@app.errorhandler(413)
def file_too_large(_error):
    return render_template(
        "index.html",
        error="File too large. The maximum upload size is 20 MB."
    ), 413


if __name__ == "__main__":
    app.run(debug=True)
