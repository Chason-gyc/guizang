"""Create an immutable raw knowledge file from an idea or captured web content."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from knowledge import validate_documents


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
SHANGHAI = ZoneInfo("Asia/Shanghai")


def _quote(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _build_id(source_type: str, identity: str, now: datetime) -> str:
    digest = hashlib.sha256(f"{source_type}\0{identity}".encode("utf-8")).hexdigest()[:10]
    return f"{now:%Y%m%d}-{digest}-raw"


def render_raw_document(
    *,
    document_id: str,
    title: str,
    source_type: str,
    source_url: str,
    content: str,
    timestamp: str,
) -> str:
    metadata = {
        "id": document_id,
        "title": title,
        "type": "raw",
        "status": "active",
        "created_at": timestamp,
        "updated_at": timestamp,
        "source_url": source_url,
        "source_type": source_type,
        "tags": [],
        "topics": [],
        "related": [],
        "references": [],
    }
    frontmatter = "\n".join(f"{key}: {_quote(value)}" for key, value in metadata.items())
    source_line = f"来源：{source_url}" if source_url else "来源：个人想法"
    return f"---\n{frontmatter}\n---\n\n# {title}\n\n{source_line}\n\n{content.strip()}\n"


def create_raw_document(
    *,
    root: Path,
    title: str,
    source_type: str,
    content: str,
    source_url: str = "",
    now: datetime | None = None,
) -> Path:
    title = title.strip()
    content = content.strip()
    source_url = source_url.strip()
    if not title:
        raise ValueError("标题不能为空")
    if not content:
        raise ValueError("原始内容不能为空")
    if source_type not in {"idea", "web"}:
        raise ValueError("source_type 必须是 idea 或 web")
    if source_type == "web" and not source_url.lower().startswith(("http://", "https://")):
        raise ValueError("网页输入必须提供 HTTP(S) URL")
    if source_type == "idea" and source_url:
        raise ValueError("个人想法不应提供 source_url")

    current_time = now or datetime.now(SHANGHAI)
    identity = source_url if source_type == "web" else content
    document_id = _build_id(source_type, identity, current_time)
    timestamp = current_time.strftime("%Y-%m-%d %H:%M")
    output_path = root / "raw" / f"{document_id}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = render_raw_document(
        document_id=document_id,
        title=title,
        source_type=source_type,
        source_url=source_url,
        content=content,
        timestamp=timestamp,
    )
    try:
        with output_path.open("x", encoding="utf-8", newline="\n") as file:
            file.write(rendered)
    except FileExistsError as exc:
        raise ValueError(f"相同输入已经存在：{output_path.relative_to(root)}") from exc
    return output_path


def _read_content(args: argparse.Namespace) -> str:
    if args.content is not None:
        return args.content
    if args.content_file is not None:
        return args.content_file.read_text(encoding="utf-8")
    raise ValueError("必须通过 --content 或 --content-file 提供原始内容")


def main() -> int:
    parser = argparse.ArgumentParser(description="将想法或已取得正文的网页写入 raw 层")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="项目根目录")
    subparsers = parser.add_subparsers(dest="source_type", required=True)

    idea_parser = subparsers.add_parser("idea", help="记录个人想法")
    idea_parser.add_argument("--title", required=True)
    idea_content = idea_parser.add_mutually_exclusive_group(required=True)
    idea_content.add_argument("--content")
    idea_content.add_argument("--content-file", type=Path)

    web_parser = subparsers.add_parser("web", help="记录已取得正文的网页")
    web_parser.add_argument("--title", required=True)
    web_parser.add_argument("--url", required=True)
    web_content = web_parser.add_mutually_exclusive_group(required=True)
    web_content.add_argument("--content")
    web_content.add_argument("--content-file", type=Path)

    args = parser.parse_args()
    root = args.root.resolve()
    try:
        content = _read_content(args)
        output_path = create_raw_document(
            root=root,
            title=args.title,
            source_type=args.source_type,
            content=content,
            source_url=getattr(args, "url", ""),
        )
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"入库失败：{exc}")
        return 1

    errors = validate_documents(root)
    if errors:
        output_path.unlink(missing_ok=True)
        print("入库后的全库校验失败，已撤销本次新文件：")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"原始资料已写入：{output_path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

