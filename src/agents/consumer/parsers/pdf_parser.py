import io
from pypdf import PdfReader

class ParsedDocument:
    def __init__(self, text: str, pages: list[str], tables: list = None):
        self.text = text
        self.pages = pages
        self.tables = tables or []

def parse_pdf(file_bytes: bytes) -> ParsedDocument:
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    full_text_list = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        pages.append(page_text)
        full_text_list.append(page_text)
        
    full_text = "\n".join(full_text_list)
    return ParsedDocument(text=full_text, pages=pages)
