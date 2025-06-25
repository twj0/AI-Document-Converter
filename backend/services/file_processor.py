# backend/services/file_processor.py (The Final, Guaranteed Fix)

import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [SERVICE] - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FileProcessingError(Exception):
    pass

try:
    import comtypes.client
    import comtypes
    COMTYPES_AVAILABLE = True
except ImportError:
    COMTYPES_AVAILABLE = False

try:
    import win32com.client as win32
    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False

try:
    from docx import Document as DocxDocument
    PYTHON_DOCX_AVAILABLE = True
except ImportError:
    PYTHON_DOCX_AVAILABLE = False

try:
    import fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


def convert_to_pdf_com(input_path: str, output_path: str) -> None:
    if not COMTYPES_AVAILABLE:
        raise RuntimeError("comtypes library not available.")

    comtypes.CoInitialize()
    logger.info("COM library initialized for the current thread.")
    
    p_in = Path(input_path)
    p_out = Path(output_path)
    app = None
    doc = None

    try:
        file_ext = p_in.suffix.lower()
        app_name = ""
        if file_ext in ['.ppt', '.pptx']:
            app_name = "Powerpoint.Application"
        elif file_ext in ['.doc', '.docx']:
            app_name = "Word.Application"
        else:
            raise FileProcessingError(f"Unsupported file type for PDF conversion: {file_ext}")

        logger.info(f"Converting '{p_in.name}' to PDF via {app_name}...")
        
        app = comtypes.client.CreateObject(app_name)
        
        # --- THIS IS THE CRUCIAL FIX ---
        # We no longer try to force the application to be invisible.
        # Let Office decide how to handle the window. For PowerPoint, this
        # often means it will briefly flash on screen, which is acceptable.
        # app.Visible = False  # <-- COMMENTED OUT or DELETED
        
        if app_name.startswith("Powerpoint"):
            doc = app.Presentations.Open(str(p_in.resolve()), WithWindow=False)
            save_format = 32 # ppSaveAsPDF
        else:
            doc = app.Documents.Open(str(p_in.resolve()), ReadOnly=True)
            save_format = 17 # wdFormatPDF
        
        doc.SaveAs(str(p_out.resolve()), FileFormat=save_format)
        logger.info(f"Successfully converted to '{p_out.name}'.")

    except Exception as e:
        raise FileProcessingError(f"Failed to convert '{p_in.name}' via COM: {e}")
    finally:
        if doc: doc.Close()
        if app: app.Quit()
        comtypes.CoUninitialize()
        logger.info("COM library uninitialized for the current thread.")


# 其他函数保持不变，但为了完整性，我们把 extract_text_smart 也包含进来

def _extract_text_with_ocr(pdf_doc: 'fitz.Document') -> str:
    if not OCR_AVAILABLE: return ""
    full_text = []
    for page in pdf_doc:
        pix = page.get_pixmap(dpi=300)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        full_text.append(pytesseract.image_to_string(img, lang='eng+chi_sim'))
    return "\n\n--- Page Break ---\n\n".join(full_text)

def extract_text_smart(input_path: str) -> str:
    p_in = Path(input_path)
    file_ext = p_in.suffix.lower()
    logger.info(f"Extracting text from '{p_in.name}'...")

    if file_ext == '.docx':
        if not PYTHON_DOCX_AVAILABLE: raise RuntimeError("python-docx not installed.")
        return "\n\n".join(p.text for p in DocxDocument(p_in).paragraphs if p.text)
    elif file_ext == '.doc':
        if not PYWIN32_AVAILABLE: raise RuntimeError("pywin32 not installed.")
        comtypes.CoInitialize()
        word_app, doc = None, None
        try:
            word_app = win32.gencache.EnsureDispatch('Word.Application')
            doc = word_app.Documents.Open(str(p_in.resolve()), ReadOnly=True)
            return doc.Content.Text
        finally:
            if doc: doc.Close(0)
            if word_app: word_app.Quit()
            comtypes.CoUninitialize()
    elif file_ext == '.pdf':
        if not PYMUPDF_AVAILABLE: raise RuntimeError("PyMuPDF not installed.")
        with fitz.open(p_in) as doc:
            text = "\n\n".join(page.get_text("text", sort=True) for page in doc)
            if len(text.strip()) > 100: return text.strip()
            return _extract_text_with_ocr(doc).strip() or text.strip()
    else:
        raise FileProcessingError(f"Unsupported file type for text extraction: {file_ext}")