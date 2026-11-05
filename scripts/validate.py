"""Validate all formal Guizang knowledge files."""

from __future__ import annotations

import argparse
from pathlib import Path

from knowledge import discover_documents, validate_documents


DEFAULT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="校验归藏知识文件")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="项目根目录")
    args = parser.parse_args()
    root = args.root.resolve()

    errors = validate_documents(root)
    if errors:
        print(f"校验失败，共 {len(errors)} 个问题：")
        for error in errors:
            print(f"- {error}")
        return 1

    documents, parse_errors = discover_documents(root)
    if parse_errors:
        for error in parse_errors:
            print(f"- {error}")
        return 1
    print(f"校验通过：{len(documents)} 个知识文件。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

