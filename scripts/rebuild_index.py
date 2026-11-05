"""Rebuild or verify the generated Guizang knowledge index."""

from __future__ import annotations

import argparse
from pathlib import Path

from knowledge import discover_documents, render_index, validate_documents


DEFAULT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="重建归藏知识索引")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="项目根目录")
    parser.add_argument("--check", action="store_true", help="仅检查索引是否为最新")
    args = parser.parse_args()
    root = args.root.resolve()

    errors = validate_documents(root)
    if errors:
        print("知识文件校验失败，索引未更新：")
        for error in errors:
            print(f"- {error}")
        return 1

    documents, parse_errors = discover_documents(root)
    if parse_errors:
        for error in parse_errors:
            print(f"- {error}")
        return 1
    expected = render_index(root, documents)
    index_path = root / "indexes" / "INDEX.md"

    if args.check:
        if not index_path.exists():
            print(f"索引不存在：{index_path.relative_to(root)}")
            return 1
        actual = index_path.read_text(encoding="utf-8")
        if actual != expected:
            print("索引不是最新状态，请运行：python scripts/rebuild_index.py")
            return 1
        print(f"索引检查通过：{len(documents)} 个知识文件。")
        return 0

    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(expected, encoding="utf-8", newline="\n")
    print(f"索引已更新：{index_path.relative_to(root)}，共 {len(documents)} 个知识文件。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

