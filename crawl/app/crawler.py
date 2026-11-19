"""Crawl and normalize Vietnamese legal documents into the app corpus schema.

The API ingest path consumes JSON records, not raw HTML/PDF.  This module is
the bridge between source files/URLs and that canonical JSON format.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import tempfile
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote, urlparse

from .normalization import repair_text

logger = logging.getLogger(__name__)

SCHEMA_FIELDS = (
    "source", "so_hieu", "ten_van_ban", "chuong", "dieu",
    "tieu_de_dieu", "khoan", "text",
)
CHAPTER_RE = re.compile(r"^\s*(Chương\s+[IVXLCDM0-9]+)\b(?:\s*[-–—:]?\s*(.*))?$", re.I)
ARTICLE_RE = re.compile(r"^\s*(Điều\s+\d+[A-Za-zĐđ]?)(?:\s*[.\-:]\s+|\s*$)(.*)$", re.I)
CLAUSE_RE = re.compile(r"^\s*(Khoản\s+\d+[A-Za-zĐđ]?)\s*[.\-:]?\s*(.*)$", re.I)
NUMBERED_CLAUSE_RE = re.compile(r"^\s*(\d+[A-Za-zĐđ]?)\s*[.)]\s+(.*)$")
NUMBER_RE = re.compile(r"(?:số|so)\s*[:.]?\s*(\d+\s*/\s*\d{4}\s*/\s*[A-Za-zĐđ0-9-]+)", re.I)
FILE_NUMBER_RE = re.compile(r"(?<!\d)(\d+)[-_](\d{4})[-_](qh\d+|nd[-_]?cp|tt[-_]?[^.]+|vbhn[-_]?[^.]+)", re.I)


@dataclass(frozen=True)
class CrawlSource:
    source: str
    title: str = ""
    effective_from: str = ""
    status: str = "unknown"


class _LegalHTMLParser(HTMLParser):
    """Small stdlib HTML extractor; keeps crawler usable without bs4."""

    _SKIP = {"script", "style", "header", "footer", "nav", "aside", "iframe", "noscript"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._target_depth: int | None = None
        self._depth = 0
        self.lines: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._depth += 1
        attrs_dict = dict(attrs)
        if tag.lower() in self._SKIP:
            self._skip_depth += 1
        if self._target_depth is None and (
            attrs_dict.get("id") in {"divContent", "divContentText", "content1"}
            or "fulltext" in (attrs_dict.get("class") or "").lower()
            or "doc_content" in (attrs_dict.get("class") or "").lower()
        ):
            self._target_depth = self._depth

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._SKIP and self._skip_depth:
            self._skip_depth -= 1
        self._depth = max(0, self._depth - 1)

    def handle_data(self, data: str) -> None:
        if self._skip_depth or (self._target_depth is not None and self._depth < self._target_depth):
            return
        value = re.sub(r"\s+", " ", data).strip()
        if value:
            self.lines.append(value)


def html_to_text(raw_html: str) -> str:
    parser = _LegalHTMLParser()
    parser.feed(raw_html)
    parser.close()
    text = "\n".join(parser.lines)
    # Thư viện pháp luật pages contain a summary/sidebar and often an English
    # duplicate after the Vietnamese document. Keep only the Vietnamese body.
    body_markers = list(re.finditer(r"MỤC\s+LỤC\s+VĂN\s+BẢN", text, re.I))
    if body_markers:
        start = body_markers[0].start()
        end = body_markers[1].start() if len(body_markers) > 1 else len(text)
        text = text[start:end]
    return text


def extract_so_hieu(text: str, source: str = "") -> str:
    text = repair_text(text)
    match = NUMBER_RE.search(" ".join(text.splitlines()[:80]))
    if match:
        return re.sub(r"\s+", "", match.group(1)).upper().replace("Đ", "Đ")
    match = FILE_NUMBER_RE.search(unquote(source))
    if match:
        kind = match.group(3).upper().replace("_", "-")
        return f"{match.group(1)}/{match.group(2)}/{kind}"
    return "N/A"


def _title_from_source(source: str) -> str:
    name = Path(unquote(urlparse(source).path)).stem or Path(source).stem
    name = re.sub(r"[-_]+", " ", name)
    return repair_text(name).strip() or "Văn bản pháp luật"


def _clean_lines(text: str) -> list[str]:
    repaired = repair_text(text)
    return [line.strip() for line in repaired.splitlines() if line.strip()]


def legal_records(
    text: str,
    source: str,
    title: str = "",
    so_hieu: str = "",
    effective_from: str = "",
    status: str = "unknown",
) -> list[dict[str, Any]]:
    """Split legal text into Điều/Khoản records matching normalization.py."""
    lines = _clean_lines(text)
    if not lines:
        return []
    current_chapter = ""
    current_article = ""
    article_title = ""
    article_lines: list[str] = []
    articles: list[tuple[str, str, str, list[str]]] = []

    def flush() -> None:
        nonlocal article_lines
        if current_article and article_lines:
            articles.append((current_chapter, current_article, article_title, article_lines[:]))
        article_lines = []

    for line in lines:
        chapter = CHAPTER_RE.match(line)
        if chapter:
            current_chapter = chapter.group(1).strip()
            continue
        article = ARTICLE_RE.match(line)
        if article:
            flush()
            current_article = article.group(1).strip()
            article_title = article.group(2).strip()
            continue
        if current_article:
            article_lines.append(line)
    flush()

    if not articles:
        articles = [(current_chapter, "Điều Toàn văn", "", lines)]

    document_title = repair_text(title) or _title_from_source(source)
    number = repair_text(so_hieu) or extract_so_hieu(text, source)
    records: list[dict[str, Any]] = []
    for chapter, article, heading, body in articles:
        clauses: list[tuple[str, list[str]]] = []
        active_clause = ""
        active_lines: list[str] = []
        for line in body:
            clause = CLAUSE_RE.match(line)
            numbered = NUMBERED_CLAUSE_RE.match(line)
            marker = clause.group(1) if clause else (numbered.group(1) if numbered else "")
            content = clause.group(2) if clause else (numbered.group(2) if numbered else line)
            if marker:
                if active_clause:
                    clauses.append((active_clause, active_lines[:]))
                active_clause, active_lines = f"Khoản {marker}", [content]
            elif active_clause:
                active_lines.append(line)
            else:
                active_lines.append(line)
        if active_clause:
            clauses.append((active_clause, active_lines[:]))
        if not clauses:
            clauses = [("Khoản Toàn văn", body)]

        for clause, clause_lines in clauses:
            content = " ".join(x.strip() for x in clause_lines if x.strip())
            if not content:
                continue
            records.append({
                "source": source,
                "so_hieu": number,
                "ten_van_ban": document_title,
                "chuong": chapter or "Chưa xác định",
                "dieu": article,
                "tieu_de_dieu": heading,
                "khoan": clause,
                "text": content,
                "effective_from": effective_from,
                "status": status,
            })
    return records


class LegalCrawler:
    def __init__(self, timeout: int = 30, user_agent: str = "Trust-Agent-Crawler/1.0") -> None:
        self.timeout = timeout
        self.user_agent = user_agent

    def fetch_url(self, url: str) -> str:
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent, "Accept-Language": "vi-VN,vi;q=0.9"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
                charset = response.headers.get_content_charset() or "utf-8"
                return html_to_text(raw.decode(charset, errors="replace"))
        except Exception as first_error:
            # Some legal sites challenge non-browser clients. Keep this
            # optional so normal local/file crawling has no browser overhead.
            try:
                from playwright.sync_api import sync_playwright
            except ImportError:
                raise first_error
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(user_agent=self.user_agent, locale="vi-VN")
                page.goto(url, wait_until="domcontentloaded", timeout=self.timeout * 1000)
                html = page.content()
                browser.close()
                return html_to_text(html)

    def read_file(self, path: Path) -> str:
        if path.suffix.lower() in {".html", ".htm"}:
            return html_to_text(path.read_text(encoding="utf-8", errors="replace"))
        if path.suffix.lower() in {".txt", ".md"}:
            return path.read_text(encoding="utf-8", errors="replace")
        if path.suffix.lower() == ".pdf":
            try:
                from pypdf import PdfReader
            except ImportError as exc:
                raise RuntimeError("PDF crawling requires the optional dependency: pip install -e '.[crawler]'") from exc
            reader = PdfReader(str(path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            return text if text.strip() else self.ocr_pdf(path)
        raise ValueError(f"Unsupported crawl file type: {path.suffix}")

    def ocr_pdf(self, path: Path) -> str:
        """OCR scanned PDF pages with Vietnamese Tesseract when text is absent."""
        try:
            import fitz  # PyMuPDF
        except ImportError as exc:
            raise RuntimeError("Scanned PDF OCR requires: pip install -e '.[crawler]'") from exc
        tesseract = shutil.which("tesseract") or r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if not Path(tesseract).is_file():
            raise RuntimeError("Tesseract OCR is not installed")
        tessdata = Path(__file__).resolve().parents[1] / "data" / "tessdata"
        if not (tessdata / "vie.traineddata").is_file():
            raise RuntimeError(f"Vietnamese OCR model not found: {tessdata / 'vie.traineddata'}")

        chunks: list[str] = []
        document = fitz.open(str(path))
        try:
            with tempfile.TemporaryDirectory(prefix="trust-agent-ocr-") as tmp:
                for index, page in enumerate(document):
                    image_path = Path(tmp) / f"page-{index:04d}.png"
                    pixmap = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
                    pixmap.save(str(image_path))
                    result = subprocess.run(
                        [tesseract, str(image_path), "stdout", "-l", "vie+eng", "--tessdata-dir", str(tessdata)],
                        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        chunks.append(result.stdout)
                    if (index + 1) % 10 == 0:
                        logger.info("OCR progress: file=%s pages=%s/%s", path.name, index + 1, len(document))
        finally:
            document.close()
        return "\n".join(chunks)

    def crawl_sources(self, sources: Iterable[CrawlSource]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for item in sources:
            try:
                text = self.fetch_url(item.source) if item.source.startswith(("http://", "https://")) else self.read_file(Path(item.source))
                records.extend(legal_records(text, item.source, item.title, effective_from=item.effective_from, status=item.status))
            except Exception as exc:
                logger.warning("Skipping crawl source %s: %s", item.source, exc)
        return records


def write_corpus(records: Iterable[dict[str, Any]], output: Path) -> int:
    """Write canonical records and remove exact duplicate chunks."""
    unique: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for record in records:
        # Source URLs/files may differ while pointing to the same legal chunk.
        # Keep the first source for citation, but do not store duplicate law text.
        key = (record["so_hieu"], record["dieu"], record["khoan"], record["text"])
        unique.setdefault(key, {field: record.get(field, "") for field in SCHEMA_FIELDS} | {
            "effective_from": record.get("effective_from", ""),
            "status": record.get("status", "unknown"),
        })
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(list(unique.values()), ensure_ascii=False, indent=2), encoding="utf-8")
    return len(unique)
