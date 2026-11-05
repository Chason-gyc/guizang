"""Application services for the local Guizang chat-style interface."""

from __future__ import annotations

import html
import re
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable

from ingest import create_raw_document
from knowledge import discover_documents, render_index, validate_documents


MAX_DOWNLOAD_BYTES = 2 * 1024 * 1024
CONTENT_DIRECTORIES = {"raw", "notes", "topics", "outputs"}
TYPE_LABELS = {
    "raw": "原始资料",
    "note": "单源笔记",
    "topic": "主题知识",
    "brief": "选题",
}


class WebPageParser(HTMLParser):
    """Extract a page title and readable text with no third-party dependency."""

    BLOCK_TAGS = {
        "article",
        "blockquote",
        "br",
        "div",
        "figcaption",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "li",
        "main",
        "p",
        "section",
        "table",
        "td",
        "th",
        "tr",
    }
    SKIP_TAGS = {"script", "style", "svg", "noscript", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._in_title = False
        self._title_parts: list[str] = []
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        if not self._skip_depth and tag in self.BLOCK_TAGS:
            self._text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
        if tag in self.SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
        if not self._skip_depth and tag in self.BLOCK_TAGS:
            self._text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        value = data.strip()
        if not value:
            return
        if self._in_title:
            self._title_parts.append(value)
        if not self._skip_depth:
            self._text_parts.append(value)

    @property
    def title(self) -> str:
        return " ".join(self._title_parts).strip()

    @property
    def text(self) -> str:
        joined = " ".join(self._text_parts)
        lines = [re.sub(r"\s+", " ", line).strip() for line in joined.splitlines()]
        return "\n\n".join(line for line in lines if line)


def extract_html(html_text: str) -> tuple[str, str]:
    parser = WebPageParser()
    parser.feed(html_text)
    parser.close()
    return html.unescape(parser.title), html.unescape(parser.text)


def fetch_webpage(url: str, timeout: int = 15) -> tuple[str, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/131 Safari/537.36 Guizang/0.1"
            )
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get_content_type()
            if content_type not in {"text/html", "text/plain"}:
                raise ValueError(f"暂不支持此内容类型：{content_type}")
            raw = response.read(MAX_DOWNLOAD_BYTES + 1)
            if len(raw) > MAX_DOWNLOAD_BYTES:
                raise ValueError("网页正文超过 2 MB，暂不自动保存")
            charset = response.headers.get_content_charset() or "utf-8"
    except urllib.error.HTTPError as exc:
        if exc.code in {403, 412, 429, 521}:
            from browser_reader import fetch_rendered_page
            return fetch_rendered_page(url)
        raise ValueError(f"网页返回 HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise ValueError(f"无法访问网页：{reason}") from exc

    text = raw.decode(charset, errors="replace")
    if content_type == "text/plain":
        title = url.rstrip("/").rsplit("/", maxsplit=1)[-1] or url
        body = text.strip()
    else:
        title, body = extract_html(text)
        if body.strip() == title.strip():
            from browser_reader import fetch_rendered_page
            return fetch_rendered_page(url)
    if not body:
        raise ValueError("没有从网页中提取到可保存的正文")
    return title or url, body


def rebuild_index(root: Path) -> None:
    errors = validate_documents(root)
    if errors:
        raise ValueError("知识文件校验失败：" + "；".join(errors))
    documents, parse_errors = discover_documents(root)
    if parse_errors:
        raise ValueError("知识文件解析失败：" + "；".join(parse_errors))
    index_path = root / "indexes" / "INDEX.md"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(render_index(root, documents), encoding="utf-8", newline="\n")


def save_idea(root: Path, content: str) -> dict[str, Any]:
    clean_content = content.strip()
    if not clean_content:
        raise ValueError("请输入要保存的想法")
    first_line = clean_content.splitlines()[0].strip()
    title = first_line[:32].rstrip("，。！？；：,.!?;:") or "未命名想法"
    path = create_raw_document(
        root=root,
        title=title,
        source_type="idea",
        content=clean_content,
    )
    rebuild_index(root)
    return {
        "title": title,
        "path": path.relative_to(root).as_posix(),
        "message": "想法已保存，并已更新知识索引。",
    }


def save_link(
    root: Path,
    url: str,
    fetcher: Callable[[str], tuple[str, str]] = fetch_webpage,
    *,
    supplied_title: str = "",
    supplied_body: str | None = None,
) -> dict[str, Any]:
    clean_url = url.strip()
    if not clean_url.lower().startswith(("http://", "https://")):
        raise ValueError("请输入完整的 HTTP(S) 链接")
    if supplied_body is not None:
        if not supplied_title.strip() or not supplied_body.strip():
            raise ValueError("请填写文章标题并粘贴正文")
        title, body = supplied_title.strip(), supplied_body.strip()
    else:
        title, body = fetcher(clean_url)
    path = create_raw_document(
        root=root,
        title=title[:80],
        source_type="web",
        source_url=clean_url,
        content=body,
    )
    rebuild_index(root)
    return {
        "title": title,
        "path": path.relative_to(root).as_posix(),
        "message": "链接正文已保存，并已更新知识索引。",
    }


def _snippet(text: str, query: str, length: int = 150) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    lower_text = compact.casefold()
    lower_query = query.casefold()
    position = lower_text.find(lower_query)
    if position < 0:
        tokens = [token for token in re.split(r"\s+", lower_query) if token]
        positions = [lower_text.find(token) for token in tokens if lower_text.find(token) >= 0]
        position = min(positions) if positions else 0
    start = max(0, position - length // 3)
    end = min(len(compact), start + length)
    prefix = "…" if start else ""
    suffix = "…" if end < len(compact) else ""
    return f"{prefix}{compact[start:end]}{suffix}"


def search_knowledge(root: Path, query: str, limit: int = 12) -> list[dict[str, Any]]:
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("请输入关键词或记得的内容片段")
    documents, parse_errors = discover_documents(root)
    if parse_errors:
        raise ValueError("知识文件解析失败：" + "；".join(parse_errors))

    query_folded = clean_query.casefold()
    tokens = [token for token in re.split(r"\s+", query_folded) if token]
    results: list[dict[str, Any]] = []
    for document in documents:
        title = str(document.metadata.get("title", ""))
        tags = document.metadata.get("tags", [])
        tag_text = " ".join(tags) if isinstance(tags, list) else ""
        searchable = f"{title}\n{tag_text}\n{document.body}"
        searchable_folded = searchable.casefold()
        score = 0
        if query_folded in title.casefold():
            score += 120
        if query_folded in tag_text.casefold():
            score += 80
        if query_folded in searchable_folded:
            score += 60
        for token in tokens:
            if token in title.casefold():
                score += 25
            if token in tag_text.casefold():
                score += 18
            occurrences = searchable_folded.count(token)
            score += min(occurrences, 8) * 6
        if score == 0:
            continue
        relative_path = document.path.relative_to(root).as_posix()
        results.append(
            {
                "id": document.id,
                "title": title,
                "type": document.type,
                "type_label": TYPE_LABELS.get(document.type, document.type),
                "updated_at": document.metadata.get("updated_at", ""),
                "path": relative_path,
                "snippet": _snippet(searchable, clean_query),
                "score": score,
            }
        )
    results.sort(key=lambda item: (item["score"], item["updated_at"]), reverse=True)
    return results[:limit]


def list_recent(root: Path, limit: int = 8) -> list[dict[str, Any]]:
    documents, parse_errors = discover_documents(root)
    if parse_errors:
        raise ValueError("知识文件解析失败：" + "；".join(parse_errors))
    items = [
        {
            "id": document.id,
            "title": document.metadata.get("title", document.id),
            "type": document.type,
            "type_label": TYPE_LABELS.get(document.type, document.type),
            "updated_at": document.metadata.get("updated_at", ""),
            "path": document.path.relative_to(root).as_posix(),
        }
        for document in documents
    ]
    items.sort(key=lambda item: (item["updated_at"], item["id"]), reverse=True)
    return items[:limit]


def read_document(root: Path, relative_path: str) -> dict[str, Any]:
    requested = (root / relative_path).resolve()
    try:
        relative = requested.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("文件路径超出知识库范围") from exc
    if not relative.parts or relative.parts[0] not in CONTENT_DIRECTORIES:
        raise ValueError("只能读取正式知识目录中的文件")
    if requested.suffix.lower() != ".md" or not requested.is_file():
        raise ValueError("知识文件不存在")
    from knowledge import parse_document

    document = parse_document(requested)
    return {
        "title": document.metadata.get("title", document.id),
        "type_label": TYPE_LABELS.get(document.type, document.type),
        "updated_at": document.metadata.get("updated_at", ""),
        "path": relative.as_posix(),
        "content": document.body,
    }

