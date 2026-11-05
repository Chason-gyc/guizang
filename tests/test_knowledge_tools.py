from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from knowledge import discover_documents, render_index, validate_documents  # noqa: E402
from ingest import create_raw_document  # noqa: E402


def write_document(
    root: Path,
    directory: str,
    document_id: str,
    document_type: str,
    references: list[str] | None = None,
    topics: list[str] | None = None,
    related: list[str] | None = None,
) -> Path:
    path = root / directory / f"{document_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "id": document_id,
        "title": f"标题 {document_id}",
        "type": document_type,
        "status": "active",
        "created_at": "2026-11-05 10:00",
        "updated_at": "2026-11-05 10:00",
        "source_url": "",
        "source_type": "idea",
        "tags": ["测试"],
        "topics": topics or [],
        "related": related or [],
        "references": references or [],
    }
    frontmatter = "\n".join(
        f"{key}: {__import__('json').dumps(value, ensure_ascii=False)}"
        for key, value in metadata.items()
    )
    path.write_text(f"---\n{frontmatter}\n---\n\n# 正文\n", encoding="utf-8")
    return path


class KnowledgeToolsTest(unittest.TestCase):
    def test_ingest_idea_creates_valid_raw_document(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_path = create_raw_document(
                root=root,
                title="归藏的第一条想法",
                source_type="idea",
                content="知识库应该从输出倒推输入。",
            )

            self.assertTrue(output_path.exists())
            self.assertEqual([], validate_documents(root))
            content = output_path.read_text(encoding="utf-8")
            self.assertIn("知识库应该从输出倒推输入。", content)

    def test_ingest_duplicate_idea_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            arguments = {
                "root": root,
                "title": "重复想法",
                "source_type": "idea",
                "content": "相同内容只允许写入一次。",
            }
            create_raw_document(**arguments)

            with self.assertRaisesRegex(ValueError, "已经存在"):
                create_raw_document(**arguments)

    def test_ingest_web_requires_http_url(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            with self.assertRaisesRegex(ValueError, "HTTP"):
                create_raw_document(
                    root=root,
                    title="无效网页",
                    source_type="web",
                    source_url="not-a-url",
                    content="正文",
                )

    def test_valid_knowledge_chain_and_index(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            write_document(root, "raw", "idea-raw", "raw")
            write_document(root, "notes", "idea-note", "note", references=["idea-raw"])
            write_document(
                root,
                "topics",
                "idea-topic",
                "topic",
                references=["idea-note"],
            )
            write_document(
                root,
                "outputs",
                "idea-brief",
                "brief",
                references=["idea-topic"],
                topics=["idea-topic"],
            )

            self.assertEqual([], validate_documents(root))
            documents, parse_errors = discover_documents(root)
            self.assertEqual([], parse_errors)
            index = render_index(root, documents)
            self.assertIn("[标题 idea-topic](../topics/idea-topic.md)", index)
            self.assertIn("[标题 idea-brief](../outputs/idea-brief.md)", index)

    def test_missing_reference_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            write_document(
                root,
                "notes",
                "broken-note",
                "note",
                references=["missing-raw"],
            )

            errors = validate_documents(root)
            self.assertTrue(any("不存在的 ID" in error for error in errors))
            self.assertTrue(any("至少引用一个 raw" in error for error in errors))

    def test_one_way_related_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            write_document(root, "raw", "first-raw", "raw", related=["second-raw"])
            write_document(root, "raw", "second-raw", "raw")

            errors = validate_documents(root)
            self.assertTrue(any("不是双向关系" in error for error in errors))


if __name__ == "__main__":
    unittest.main()

