import re
from typing import Any, Dict, List

from pydantic import BaseModel, Field
from pypdf import PdfReader


class ParseResumeResponse(BaseModel):
    raw_text: str = Field(default="")
    page_count: int = Field(default=0)
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    file_type: str = Field(default="pdf")


class DocIntelligenceService:
    def __init__(self):
        self.file_type_aliases = {".pdf": "pdf", ".docx": "docx"}

    def parse_resume(self, file_bytes: bytes, filename: str) -> ParseResumeResponse:
        clean_name = (filename or "resume").lower()
        file_type = self.file_type_aliases.get(clean_name[clean_name.rfind("."):], "pdf")

        if file_type == "pdf":
            raw_text = self._extract_pdf_text(file_bytes)
        else:
            raw_text = self._extract_text_fallback(file_bytes)

        return ParseResumeResponse(
            raw_text=raw_text,
            page_count=max(1, len(self._split_pages(raw_text))),
            tables=self._extract_tables(raw_text),
            file_type=file_type,
        )

    async def parse_resume_layout(self, file_bytes: bytes, filename: str) -> ParseResumeResponse:
        return self.parse_resume(file_bytes, filename)

    def _extract_pdf_text(self, file_bytes: bytes) -> str:
        try:
            import io
            reader = PdfReader(io.BytesIO(file_bytes))
            pages = []
            for page in reader.pages:
                text = page.extract_text() or ""
                pages.append(text)
            return "\n\n".join(pages).strip()
        except Exception:
            return self._extract_text_fallback(file_bytes)

    def _extract_text_fallback(self, file_bytes: bytes) -> str:
        text = file_bytes.decode("utf-8", errors="ignore")
        cleaned = re.sub(r"\s+", " ", text).strip()
        return cleaned or "Resume text could not be extracted automatically."

    def _split_pages(self, raw_text: str) -> List[str]:
        return [page.strip() for page in re.split(r"\n\s*\n", raw_text) if page.strip()]

    def _extract_tables(self, raw_text: str) -> List[Dict[str, Any]]:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        tables: List[Dict[str, Any]] = []
        current: List[str] = []
        for line in lines:
            if re.search(r"\b(Experience|Education|Skills|Projects|Summary)\b", line, re.IGNORECASE):
                if current:
                    tables.append({"section": "resume", "rows": current})
                    current = []
                current.append(line)
            elif current and ("|" in line or re.search(r"\s{2,}", line)):
                current.append(line)
        if current:
            tables.append({"section": "resume", "rows": current})
        return tables[:3]
