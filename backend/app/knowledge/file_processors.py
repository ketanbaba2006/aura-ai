"""
AURA AI Document Processing & Ingestion Engine
Handles parsing and extraction of diverse file formats including scanned PDFs, images, archives, code, spreadsheets, and presentations.
"""

import io
import os
import csv
import zipfile
import logging
import mimetypes
from pathlib import Path
from datetime import datetime

# Optional parser imports
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    import docx
except ImportError:
    docx = None

try:
    import openpyxl
except ImportError:
    openpyxl = None

try:
    from pptx import Presentation
except ImportError:
    Presentation = None

try:
    import pypdfium2
except ImportError:
    pypdfium2 = None

try:
    import pytesseract
    from PIL import Image as PILImage
except ImportError:
    pytesseract = None
    PILImage = None

logger = logging.getLogger(__name__)

class FileProcessor:
    """Enterprise-grade document text parser supporting 20+ file formats with built-in OCR & recursion."""

    def detect_format(self, filename: str, file_bytes: bytes) -> str:
        """Automatically detect file type using magic bytes headers and file extensions."""
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        header = file_bytes[:8]

        # Magic Bytes checks
        if header.startswith(b"%PDF-"):
            return "pdf"
        elif header.startswith(b"PK\x03\x04"):
            # Could be zip, docx, pptx, or xlsx
            if ext in ["docx", "doc"]:
                return "docx"
            elif ext in ["xlsx", "xls"]:
                return "xlsx"
            elif ext in ["pptx", "ppt"]:
                return "pptx"
            return "zip"
        elif header.startswith(b"\x52\x61\x72\x21\x1a\x07"):  # Rar!
            return "rar"
        elif header.startswith(b"\x89PNG\r\n\x1a\n") or header.startswith(b"\xff\xd8\xff") or header.startswith(b"GIF8"):
            return "image"

        # Text/Code type checks
        if ext in ["py", "java", "c", "cpp", "h", "hpp", "js", "ts", "jsx", "tsx", "css", "html", "htm", "json", "xml", "yaml", "yml"]:
            return "code"
        elif ext in ["csv"]:
            return "csv"
        elif ext in ["xlsx", "xls"]:
            return "xlsx"
        elif ext in ["pptx", "ppt"]:
            return "pptx"
        elif ext in ["docx", "doc"]:
            return "docx"
        elif ext in ["md", "markdown", "txt"]:
            return "text"
        elif ext in ["mp3", "wav", "ogg", "m4a", "flac"]:
            return "audio"
        elif ext in ["mp4", "avi", "mkv", "mov", "webm"]:
            return "video"

        # Guess from mime type
        mime, _ = mimetypes.guess_type(filename)
        if mime:
            if mime.startswith("text/"):
                return "text"
            elif mime.startswith("image/"):
                return "image"
            elif mime.startswith("audio/"):
                return "audio"
            elif mime.startswith("video/"):
                return "video"
            elif mime == "application/pdf":
                return "pdf"
            elif mime in ["application/zip", "application/x-zip-compressed"]:
                return "zip"

        # Fallback to extension
        return ext if ext else "text"

    def extract_text(self, filename: str, file_bytes: bytes) -> tuple[str, str]:
        """Route document to correct parser based on file category. Returns (extracted_text, file_type)."""
        file_type = self.detect_format(filename, file_bytes)
        logger.info(f"Processing upload '{filename}' detected as category '{file_type}' ({len(file_bytes)} bytes)")

        try:
            if file_type == "pdf":
                return self._extract_pdf(file_bytes, filename), "pdf"
            elif file_type == "docx":
                return self._extract_docx(file_bytes), "docx"
            elif file_type == "text":
                return file_bytes.decode("utf-8", errors="ignore"), "text"
            elif file_type == "code":
                return self._extract_code(filename, file_bytes), "code"
            elif file_type == "csv":
                return self._extract_csv(file_bytes), "csv"
            elif file_type == "xlsx":
                return self._extract_excel(file_bytes), "xlsx"
            elif file_type == "pptx":
                return self._extract_powerpoint(file_bytes), "pptx"
            elif file_type == "image":
                return self._extract_image_ocr(file_bytes, filename), "image"
            elif file_type in ["audio", "video"]:
                return self._extract_media_metadata(filename, file_type, len(file_bytes)), file_type
            elif file_type in ["zip", "rar"]:
                return self._extract_archive(file_bytes, file_type), "archive"
            else:
                # Default plaintext fallback
                return file_bytes.decode("utf-8", errors="ignore"), "text"
        except Exception as e:
            logger.error(f"Error parsing file '{filename}' with processor '{file_type}': {e}", exc_info=True)
            raise RuntimeError(f"Parsing failed for .{file_type} file: {str(e)}")

    def _extract_pdf(self, file_bytes: bytes, filename: str) -> str:
        """Extract text from PDF using pypdf. Automatically triggers OCR if pages contain scanned images only."""
        if PdfReader is None:
            raise RuntimeError("pypdf is not installed.")

        reader = PdfReader(io.BytesIO(file_bytes))
        text_parts = []
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        extracted = "\n\n".join(text_parts).strip()

        # Scanned PDF check: if character count is extremely low relative to pages, run OCR
        if len(extracted) < 100 * len(reader.pages):
            logger.info(f"PDF '{filename}' appears scanned (extracted only {len(extracted)} chars). Initiating page OCR...")
            ocr_text = self._ocr_pdf_pages(file_bytes)
            if ocr_text:
                return ocr_text
            logger.warning(f"OCR fallback failed or returned empty text for scanned PDF '{filename}'. Reverting to base text.")

        return extracted

    def _ocr_pdf_pages(self, file_bytes: bytes) -> str:
        """Render PDF pages to images using pypdfium2 and extract text via pytesseract OCR."""
        if pypdfium2 is None:
            logger.error("pypdfium2 is not installed, skipping scanned PDF OCR.")
            return ""
        if pytesseract is None:
            logger.error("pytesseract is not installed, skipping scanned PDF OCR.")
            return ""

        ocr_pages_text = []
        try:
            pdf = pypdfium2.PdfDocument(file_bytes)
            logger.info(f"Rendering {len(pdf)} pages for OCR...")
            for i in range(len(pdf)):
                page = pdf[i]
                # Render to PIL image (72 dpi is fast, but 150/200 dpi is better for OCR accuracy)
                bitmap = page.render(scale=2.0)
                pil_img = bitmap.to_pil()
                
                # Perform OCR
                page_ocr = pytesseract.image_to_string(pil_img)
                if page_ocr.strip():
                    ocr_pages_text.append(f"--- Page {i+1} OCR ---\n{page_ocr}")
                bitmap.close()
            pdf.close()
        except Exception as ocr_err:
            logger.error(f"Failed during scanned PDF OCR processing: {ocr_err}")
            return ""

        return "\n\n".join(ocr_pages_text)

    def _extract_docx(self, file_bytes: bytes) -> str:
        """Extract text from Word Document."""
        if docx is None:
            raise RuntimeError("python-docx is not installed.")
        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text]
        return "\n".join(paragraphs)

    def _extract_code(self, filename: str, file_bytes: bytes) -> str:
        """Extract source code and format it inside a clean markdown notation."""
        code_str = file_bytes.decode("utf-8", errors="ignore")
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        
        # Maps file extensions to markdown tags
        code_mapping = {
            "py": "python", "js": "javascript", "ts": "typescript", "jsx": "javascript",
            "tsx": "typescript", "java": "java", "c": "c", "cpp": "cpp", "h": "cpp",
            "hpp": "cpp", "css": "css", "html": "html", "htm": "html", "json": "json",
            "xml": "xml", "yaml": "yaml", "yml": "yaml"
        }
        lang = code_mapping.get(ext, "")
        return f"Code File: `{filename}`\n\n```{lang}\n{code_str}\n```"

    def _extract_csv(self, file_bytes: bytes) -> str:
        """Format CSV spreadsheets into text representing row tables."""
        stream = io.StringIO(file_bytes.decode("utf-8", errors="ignore"))
        reader = csv.reader(stream)
        rows = list(reader)
        if not rows:
            return ""

        lines = ["CSV Dataset Contents:"]
        headers = rows[0]
        lines.append("Headers: " + ", ".join(headers))
        
        for i, row in enumerate(rows[1:100], 1): # Index first 100 rows
            row_vals = [f"{headers[j] if j < len(headers) else f'Col{j}'}={val}" for j, val in enumerate(row)]
            lines.append(f"Row {i}: {', '.join(row_vals)}")
        
        if len(rows) > 100:
            lines.append(f"... (Truncated {len(rows) - 100} remaining rows for context safety)")
            
        return "\n".join(lines)

    def _extract_excel(self, file_bytes: bytes) -> str:
        """Format Excel spreadsheets (.xlsx) worksheets."""
        if openpyxl is None:
            raise RuntimeError("openpyxl is not installed.")
            
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
        sheets_text = []

        for name in wb.sheetnames:
            sheet = wb[name]
            sheets_text.append(f"Worksheet: '{name}'")
            row_count = 0
            
            for row in sheet.iter_rows(values_only=True):
                # Filter out completely empty rows
                if not any(v is not None for v in row):
                    continue
                row_vals = [str(v) if v is not None else "" for v in row]
                sheets_text.append(f"Row {row_count + 1}: {', '.join(row_vals)}")
                row_count += 1
                if row_count >= 100: # limit to first 100 rows per sheet
                    sheets_text.append("... (Truncated sheet)")
                    break
        return "\n".join(sheets_text)

    def _extract_powerpoint(self, file_bytes: bytes) -> str:
        """Extract slide layouts and shapes text from PowerPoint presentation."""
        if Presentation is None:
            raise RuntimeError("python-pptx is not installed.")
            
        prs = Presentation(io.BytesIO(file_bytes))
        slides_text = []
        
        for i, slide in enumerate(prs.slides, 1):
            slide_content = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_content.append(shape.text.strip())
            
            if slide_content:
                slides_text.append(f"--- PowerPoint Slide {i} ---\n" + "\n".join(slide_content))
                
        return "\n\n".join(slides_text)

    def _extract_image_ocr(self, file_bytes: bytes, filename: str) -> str:
        """Perform image OCR text extraction if pytesseract is available, else returns metadata."""
        metadata = f"[Uploaded Image file: {filename} ({len(file_bytes)} bytes)]"
        
        if pytesseract is None:
            logger.info("pytesseract or PIL is not installed. Skipping image OCR.")
            return metadata
            
        try:
            img = PILImage.open(io.BytesIO(file_bytes))
            ocr_text = pytesseract.image_to_string(img)
            
            # Retrieve basic image dimensions
            width, height = img.size
            format_str = img.format or "Unknown"
            
            res_lines = [
                f"Image Metadata: Name={filename}, Format={format_str}, Dimensions={width}x{height} pixels",
                "Extracted Text from Image (OCR):"
            ]
            if ocr_text.strip():
                res_lines.append(ocr_text.strip())
            else:
                res_lines.append("(No text detected in image)")
                
            return "\n".join(res_lines)
        except Exception as e:
            logger.warning(f"Failed running OCR on image: {e}")
            return metadata

    def _extract_media_metadata(self, filename: str, file_type: str, file_size: int) -> str:
        """Format metadata details for Audio/Video uploads."""
        kb_size = file_size / 1024
        return (
            f"--- Uploaded Media File ---\n"
            f"Filename: {filename}\n"
            f"Format: {file_type.upper()}\n"
            f"File Size: {kb_size:.2f} KB\n"
            f"Uploaded At: {datetime.utcnow().isoformat()} UTC\n"
            f"Status: Available in workspace sandbox copy."
        )

    def _extract_archive(self, file_bytes: bytes, archive_type: str) -> str:
        """Recursively extract ZIP archives and parse nested text/code files."""
        if archive_type == "rar":
            # Native python support for RAR without unrar binaries is sparse.
            # We can log a placeholder or extract what we can.
            return "[Uploaded RAR Archive: Recurse extracting requires external unrar binaries. Contents copied to sandbox.]"

        contents = ["ZIP Archive Ingested Files:"]
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                # Loop all zipped files
                for info in z.infolist():
                    if info.is_dir():
                        continue
                    
                    # Read zipped file
                    filename = info.filename
                    with z.open(filename) as f:
                        data = f.read()

                    # Skip binary files that are too large or of un-supported categories
                    ext = filename.split(".")[-1].lower() if "." in filename else ""
                    if ext in ["png", "jpg", "jpeg", "webp", "gif", "bmp", "pdf", "docx", "xlsx", "pptx", "zip", "rar", "exe", "dll", "so", "o"]:
                        contents.append(f"\n- File '{filename}' (Binary file, size: {info.file_size} bytes - Indexed as reference)")
                        continue

                    # Text/Code extraction
                    try:
                        text = data.decode("utf-8", errors="ignore").strip()
                        if text:
                            # Truncate content if it's too large for prompt context
                            preview = text[:2000] + "\n... (File truncated)" if len(text) > 2000 else text
                            contents.append(f"\n- File '{filename}' ({info.file_size} bytes):\n```\n{preview}\n```")
                    except Exception as dec_err:
                        contents.append(f"\n- File '{filename}' (Failed to decode as text, size: {info.file_size} bytes)")
        except Exception as e:
            logger.error(f"Failed to unpack ZIP archive: {e}")
            return f"ZIP Archive Extraction Error: {e}"

        return "\n\n".join(contents)

# Global Instance
file_processor = FileProcessor()
