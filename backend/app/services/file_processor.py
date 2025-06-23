# backend/app/services/file_processor.py

import logging
from pathlib import Path
from typing import Literal

# --- Configure Logging ---
# This provides clear feedback on the process, which is crucial for debugging.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Custom Exception Class ---
class FileProcessingError(Exception):
    """Custom exception for file processing failures."""
    pass

# --- Library Availability Checks (Graceful Degradation) ---
# This allows the system to run even if some optional libraries are not installed.

try:
    import comtypes.client
    COMTYPES_AVAILABLE = True
except ImportError:
    COMTYPES_AVAILABLE = False
    logger.warning("`comtypes` library not found. PPT/PPTX/DOC to PDF conversion will be disabled.")

try:
    import win32com.client as win32
    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False
    logger.warning("`pywin32` library not found. .doc text extraction will be disabled.")

try:
    from docx import Document as DocxDocument
    PYTHON_DOCX_AVAILABLE = True
except ImportError:
    PYTHON_DOCX_AVAILABLE = False
    logger.warning("`python-docx` library not found. .docx text extraction will be disabled.")

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("`PyMuPDF` library not found. PDF processing will be disabled.")

try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("`pytesseract` or `Pillow` not found. OCR functionality for PDFs will be disabled.")


# --- Core Processing Functions ---

def convert_to_pdf_com(input_path: Path, output_path: Path) -> None:
    """
    Converts a given Office document (.ppt, .pptx, .doc, .docx) to PDF using COM interface.
    This is the most reliable method on a Windows machine with MS Office installed.

    Args:
        input_path: Path to the source Office document.
        output_path: Path to save the generated PDF file.

    Raises:
        FileProcessingError: If conversion fails for any reason.
        RuntimeError: If required libraries (comtypes, pywin32) are not available.
    """
    if not COMTYPES_AVAILABLE or not PYWIN32_AVAILABLE:
        raise RuntimeError("COM libraries (comtypes, pywin32) are not available for Office conversion.")

    input_abs = str(input_path.resolve())
    output_abs = str(output_path.resolve())
    app = None
    doc = None

    file_ext = input_path.suffix.lower()
    app_name = ""
    save_format = 0

    if file_ext in ['.ppt', '.pptx']:
        app_name = "Powerpoint.Application"
        save_format = 32  # PpSaveAsFileType.ppSaveAsPDF
    elif file_ext in ['.doc', '.docx']:
        app_name = "Word.Application"
        save_format = 17  # WdSaveFormat.wdFormatPDF
    else:
        raise FileProcessingError(f"Unsupported file type for PDF conversion: {file_ext}")

    logger.info(f"Attempting to convert '{input_path.name}' to PDF using {app_name}...")

    try:
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        app = comtypes.client.CreateObject(app_name)
        app.Visible = False  # Run in the background

        if app_name == "Powerpoint.Application":
            doc = app.Presentations.Open(input_abs, WithWindow=False)
        else: # Word.Application
            doc = app.Documents.Open(input_abs, ReadOnly=True)

        doc.SaveAs(output_abs, FileFormat=save_format)
        logger.info(f"Successfully converted and saved to '{output_path.name}'.")

    except Exception as e:
        error_message = f"Failed to convert '{input_path.name}' via COM interface. Reason: {e}"
        logger.error(error_message)
        raise FileProcessingError(error_message)
    finally:
        # Crucial cleanup to prevent dangling Office processes
        if doc:
            try:
                doc.Close()
            except Exception:
                pass
        if app:
            try:
                app.Quit()
            except Exception:
                pass
        doc = None
        app = None


def extract_text_from_docx(input_path: Path) -> str:
    """Extracts text content from a .docx file."""
    if not PYTHON_DOCX_AVAILABLE:
        raise RuntimeError("`python-docx` is not installed, cannot process .docx files.")
    
    logger.info(f"Extracting text from DOCX: '{input_path.name}'...")
    try:
        doc = DocxDocument(input_path)
        return "\n\n".join(para.text for para in doc.paragraphs if para.text)
    except Exception as e:
        raise FileProcessingError(f"Could not extract text from DOCX '{input_path.name}': {e}")


def extract_text_from_doc(input_path: Path) -> str:
    """Extracts text content from a legacy .doc file using Word COM interface."""
    if not PYWIN32_AVAILABLE:
        raise RuntimeError("`pywin32` is not installed, cannot process .doc files.")

    logger.info(f"Extracting text from DOC: '{input_path.name}' using Word COM...")
    word_app = None
    doc = None
    try:
        word_app = win32.gencache.EnsureDispatch('Word.Application')
        word_app.Visible = False
        doc = word_app.Documents.Open(str(input_path.resolve()), ReadOnly=True)
        text_content = doc.Content.Text
        return text_content
    except Exception as e:
        raise FileProcessingError(f"Could not extract text from DOC '{input_path.name}' via COM: {e}")
    finally:
        if doc:
            doc.Close(0) # 0 = wdDoNotSaveChanges
        if word_app:
            word_app.Quit()


def _extract_text_with_ocr(pdf_doc: 'fitz.Document') -> str:
    """
    Private helper to perform OCR on a PDF document.
    This is the "Tier 2" fallback for scanned or image-based PDFs.
    """
    if not OCR_AVAILABLE:
        logger.warning("OCR libraries not available. Skipping OCR fallback.")
        return ""

    logger.info(f"Performing OCR on a {len(pdf_doc)}-page document...")
    full_text = []
    for page_num, page in enumerate(pdf_doc):
        try:
            logger.info(f"OCR processing page {page_num + 1}...")
            # Render page to a high-res image for better OCR accuracy
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Use Tesseract to extract text from the image
            page_text = pytesseract.image_to_string(img, lang='eng+chi_sim') # Example: English + Simplified Chinese
            if page_text:
                full_text.append(page_text)
        except Exception as e:
            logger.error(f"Error during OCR on page {page_num + 1}: {e}")
            continue # Continue to next page
            
    return "\n\n--- Page Break ---\n\n".join(full_text)


def extract_text_from_pdf(input_path: Path, ocr_threshold: int = 100) -> str:
    """
    Extracts text from a PDF using a tiered approach.
    Tier 1: Directly extracts text using PyMuPDF.
    Tier 2: If Tier 1 yields very little text, falls back to OCR.
    """
    if not PYMUPDF_AVAILABLE:
        raise RuntimeError("`PyMuPDF` is not installed, cannot process PDF files.")

    logger.info(f"Extracting text from PDF: '{input_path.name}'...")
    try:
        doc = fitz.open(input_path)
    except Exception as e:
        raise FileProcessingError(f"Could not open PDF file '{input_path.name}': {e}")

    # Tier 1: Direct text extraction
    tier1_text = ""
    try:
        tier1_text = "\n\n".join(page.get_text("text", sort=True) for page in doc)
    except Exception as e:
        logger.warning(f"Error during direct text extraction from '{input_path.name}': {e}. Will attempt OCR.")
        tier1_text = ""
    
    # Check if direct extraction was successful
    if len(tier1_text.strip()) > ocr_threshold:
        logger.info("Direct text extraction successful.")
        doc.close()
        return tier1_text.strip()
    
    # Tier 2: OCR Fallback
    logger.warning(f"Direct text extraction yielded minimal results (length: {len(tier1_text.strip())}). "
                   f"Attempting OCR fallback...")
    
    try:
        ocr_text = _extract_text_with_ocr(doc)
        if ocr_text.strip():
            logger.info("OCR fallback extraction successful.")
            return ocr_text.strip()
        else:
            logger.warning("OCR fallback did not yield any text.")
            # Return the minimal text from Tier 1 if OCR fails completely
            return tier1_text.strip()
    finally:
        doc.close()