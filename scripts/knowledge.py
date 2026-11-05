"""Shared parsing, validation, and indexing helpers for Guizang."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


CONTENT_DIR_TYPES = {
    "raw": "raw",
    "notes": "note",
    "topics": "topic",
    "outputs": "brief",
}
REQUIRED_FIELDS = (
    "id",
    "title",
    "type",
    "status",
    "created_at",
    "updated_at",
    "source_url",
    "source_type",
    "tags",
    "topics",
    "related",
    "references",
)
LIST_FIELDS = ("tags", "topics", "related", "references")
ALLOWED_STATUSES = {"active", "pending", "archived"}
ALLOWED_SOURCE_TYPES = {"web", "idea"}
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M"
HTTP_URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)


@dataclass(frozen=True)
class KnowledgeDocument:
    path: Path
    metadata: dict[str, Any]
    body: str

    @property
    def id(self) -> str:
        return str(self.metadata.get("id", ""))

    @property
    def type(self) -> str:
        return str(self.metadata.get("type", ""))


def _parse_value(raw_value: str, path: Path, line_number: int) -> Any:
    value = raw_value.strip()
    if value == "":
        return ""
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{path}:{line_number}: frontmatter 值必须使用 JSON 兼容写法：{value}"
        ) from exc


def parse_document(path: Path) -> KnowledgeDocument:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{path}: 缺少 frontmatter 起始标记 ---")

    try:
        end_index = next(
            index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"
        )
    except StopIteration as exc:
        raise ValueError(f"{path}: 缺少 frontmatter 结束标记 ---") from exc

    metadata: dict[str, Any] = {}
    for index, line in enumerate(lines[1:end_index], start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"{path}:{index}: frontmatter 字段缺少冒号")
        key, raw_value = line.split(":", maxsplit=1)
        key = key.strip()
        if not key:
            raise ValueError(f"{path}:{index}: frontmatter 字段名不能为空")
        if key in metadata:
            raise ValueError(f"{path}:{index}: frontmatter 字段重复：{key}")
        metadata[key] = _parse_value(raw_value, path, index)

    body = "\n".join(lines[end_index + 1 :]).strip()
    return KnowledgeDocument(path=path, metadata=metadata, body=body)


def discover_documents(root: Path) -> tuple[list[KnowledgeDocument], list[str]]:
    documents: list[KnowledgeDocument] = []
    errors: list[str] = []
    for directory_name in CONTENT_DIR_TYPES:
        directory = root / directory_name
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*.md")):
            try:
                documents.append(parse_document(path))
            except (OSError, UnicodeError, ValueError) as exc:
                errors.append(str(exc))
    return documents, errors


def _validate_timestamp(value: Any, field: str, document: KnowledgeDocument) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, TIMESTAMP_FORMAT)
    except ValueError:
        return None


def validate_documents(root: Path) -> list[str]:
    documents, errors = discover_documents(root)
    by_id: dict[str, KnowledgeDocument] = {}

    for document in documents:
        relative_path = document.path.relative_to(root)
        metadata = document.metadata
        missing_fields = [field for field in REQUIRED_FIELDS if field not in metadata]
        if missing_fields:
            errors.append(f"{relative_path}: 缺少字段：{', '.join(missing_fields)}")

        document_id = metadata.get("id")
        if not isinstance(document_id, str) or not ID_PATTERN.fullmatch(document_id):
            errors.append(f"{relative_path}: id 只能包含小写英文字母、数字和连字符")
        elif document_id in by_id:
            other_path = by_id[document_id].path.relative_to(root)
            errors.append(f"{relative_path}: id 与 {other_path} 重复：{document_id}")
        else:
            by_id[document_id] = document

        title = metadata.get("title")
        if not isinstance(title, str) or not title.strip():
            errors.append(f"{relative_path}: title 必须是非空字符串")

        expected_type = CONTENT_DIR_TYPES.get(relative_path.parts[0])
        if metadata.get("type") != expected_type:
            errors.append(
                f"{relative_path}: type 应为 {expected_type!r}，实际为 {metadata.get('type')!r}"
            )

        if metadata.get("status") not in ALLOWED_STATUSES:
            errors.append(f"{relative_path}: status 不在允许范围内")
        if metadata.get("source_type") not in ALLOWED_SOURCE_TYPES:
            errors.append(f"{relative_path}: source_type 不在允许范围内")
        if metadata.get("source_type") == "web":
            source_url = metadata.get("source_url")
            if not isinstance(source_url, str) or not HTTP_URL_PATTERN.match(source_url):
                errors.append(f"{relative_path}: web 来源必须提供 HTTP(S) source_url")

        created_at = _validate_timestamp(metadata.get("created_at"), "created_at", document)
        updated_at = _validate_timestamp(metadata.get("updated_at"), "updated_at", document)
        if created_at is None:
            errors.append(f"{relative_path}: created_at 格式必须为 YYYY-MM-DD HH:mm")
        if updated_at is None:
            errors.append(f"{relative_path}: updated_at 格式必须为 YYYY-MM-DD HH:mm")
        if created_at and updated_at and updated_at < created_at:
            errors.append(f"{relative_path}: updated_at 不得早于 created_at")

        for field in LIST_FIELDS:
            value = metadata.get(field)
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                errors.append(f"{relative_path}: {field} 必须是字符串数组")
            elif len(value) != len(set(value)):
                errors.append(f"{relative_path}: {field} 不得包含重复项")

        references = metadata.get("references")
        if expected_type != "raw" and isinstance(references, list) and not references:
            errors.append(f"{relative_path}: {expected_type} 必须至少包含一个 reference")
        if not document.body:
            errors.append(f"{relative_path}: 正文不能为空")

    for document in documents:
        relative_path = document.path.relative_to(root)
        for field in ("topics", "related", "references"):
            values = document.metadata.get(field)
            if not isinstance(values, list):
                continue
            for target_id in values:
                target = by_id.get(target_id)
                if target is None:
                    errors.append(f"{relative_path}: {field} 引用了不存在的 ID：{target_id}")
                    continue
                if field == "topics" and target.type != "topic":
                    errors.append(f"{relative_path}: topics 只能引用 topic：{target_id}")
                if field == "related":
                    reverse_related = target.metadata.get("related")
                    if isinstance(reverse_related, list) and document.id not in reverse_related:
                        target_path = target.path.relative_to(root)
                        errors.append(
                            f"{relative_path}: related 与 {target_path} 不是双向关系：{target_id}"
                        )

        reference_ids = document.metadata.get("references")
        if not isinstance(reference_ids, list):
            continue
        reference_types = {by_id[item].type for item in reference_ids if item in by_id}
        if document.type == "note" and reference_ids and "raw" not in reference_types:
            errors.append(f"{relative_path}: note 必须至少引用一个 raw")
        if document.type == "topic" and reference_ids and not reference_types.intersection(
            {"note", "topic"}
        ):
            errors.append(f"{relative_path}: topic 必须至少引用一个 note 或 topic")
        if document.type == "brief" and reference_ids and "topic" not in reference_types:
            errors.append(f"{relative_path}: brief 必须至少引用一个 topic")

    return sorted(set(errors))


def render_index(root: Path, documents: Iterable[KnowledgeDocument]) -> str:
    grouped: dict[str, list[KnowledgeDocument]] = {item: [] for item in CONTENT_DIR_TYPES.values()}
    for document in documents:
        if document.type in grouped:
            grouped[document.type].append(document)

    labels = {
        "raw": "原始资料",
        "note": "单源笔记",
        "topic": "主题知识",
        "brief": "选题输出",
    }
    lines = [
        "# 归藏知识索引",
        "",
        "> 此文件由 `python scripts/rebuild_index.py` 自动生成，请勿手动编辑。",
        "",
    ]
    for document_type in ("topic", "note", "brief", "raw"):
        items = sorted(
            grouped[document_type],
            key=lambda item: (str(item.metadata.get("updated_at", "")), item.id),
            reverse=True,
        )
        lines.extend((f"## {labels[document_type]}", ""))
        if not items:
            lines.extend(("暂无内容。", ""))
            continue
        for document in items:
            relative_path = document.path.relative_to(root).as_posix()
            title = document.metadata.get("title", document.id)
            tags = document.metadata.get("tags", [])
            tag_text = f" -- {', '.join(tags)}" if tags else ""
            lines.append(f"- [{title}](../{relative_path}){tag_text}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"

