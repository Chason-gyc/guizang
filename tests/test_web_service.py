from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from web_service import delete_document, extract_html, save_idea, save_link, search_knowledge  # noqa: E402


class WebServiceTest(unittest.TestCase):
    def test_manual_article_preserves_source_without_fetch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def forbidden_fetch(url):
                self.fail("Manual import must not fetch the URL")
            result = save_link(root, "https://example.com/private", forbidden_fetch,
                               supplied_title="人工导入", supplied_body="已登录后复制的文章正文。")
            saved = (root / result["path"]).read_text(encoding="utf-8")
            self.assertIn("https://example.com/private", saved)
            self.assertIn("已登录后复制的文章正文。", saved)
            self.assertEqual(1, len(search_knowledge(root, "文章正文")))

    def test_empty_manual_body_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                save_link(root, "https://example.com/private", supplied_title="标题", supplied_body=" ")
            self.assertFalse((root / "raw").exists())

    def test_extract_html_removes_scripts_and_keeps_readable_text(self) -> None:
        title, text = extract_html(
            "<html><head><title>测试文章</title><script>bad()</script></head>"
            "<body><article><h1>主标题</h1><p>这是正文。</p></article></body></html>"
        )
        self.assertEqual("测试文章", title)
        self.assertIn("主标题", text)
        self.assertIn("这是正文。", text)
        self.assertNotIn("bad", text)

    def test_save_idea_rebuilds_index_and_can_be_searched_by_fragment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            result = save_idea(root, "知识库的终点应该是主动生成选题。")

            self.assertTrue((root / result["path"]).exists())
            self.assertIn("主动生成选题", (root / "indexes" / "INDEX.md").read_text(encoding="utf-8"))
            matches = search_knowledge(root, "主动生成")
            self.assertEqual(1, len(matches))
            self.assertEqual(result["path"], matches[0]["path"])

    def test_save_link_uses_fetcher_and_is_searchable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)

            def fake_fetcher(url: str) -> tuple[str, str]:
                self.assertEqual("https://example.com/article", url)
                return "公开文章", "文章讨论了知识编译与资料堆积的区别。"

            result = save_link(root, "https://example.com/article", fetcher=fake_fetcher)
            matches = search_knowledge(root, "知识编译")
            self.assertEqual(1, len(matches))
            self.assertEqual(result["path"], matches[0]["path"])

    def test_empty_search_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaisesRegex(ValueError, "关键词"):
                search_knowledge(Path(temporary_directory), "   ")

    def test_delete_unreferenced_document_rebuilds_index(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            saved = save_idea(root, "待删除的想法")
            result = delete_document(root, saved["path"])
            self.assertIn("已删除", result["message"])
            self.assertFalse((root / saved["path"]).exists())

    def test_delete_referenced_document_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            raw = save_idea(root, "被引用的原始想法")
            raw_id = Path(raw["path"]).stem
            note = root / "notes" / "20261105-reference-note.md"
            note.parent.mkdir(parents=True)
            note.write_text(
                "---\n"
                f'id: "20261105-reference-note"\n'
                'title: "引用笔记"\n'
                'type: "note"\n'
                'status: "active"\n'
                'created_at: "2026-11-05 16:00"\n'
                'updated_at: "2026-11-05 16:00"\n'
                'source_url: ""\n'
                'source_type: "idea"\n'
                'tags: []\n'
                'topics: []\n'
                'related: []\n'
                f'references: ["{raw_id}"]\n'
                "---\n\n正文\n",
                encoding="utf-8",
            )
            topic = root / "topics" / "20261105-reference-topic.md"
            topic.parent.mkdir(parents=True)
            topic.write_text(
                "---\n"
                'id: "20261105-reference-topic"\n'
                'title: "主题引用"\n'
                'type: "topic"\n'
                'status: "active"\n'
                'created_at: "2026-11-05 16:00"\n'
                'updated_at: "2026-11-05 16:00"\n'
                'source_url: ""\n'
                'source_type: "idea"\n'
                'tags: []\n'
                'topics: []\n'
                'related: []\n'
                'references: ["20261105-reference-note"]\n'
                "---\n\n主题\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "引用"):
                delete_document(root, raw["path"])

    def test_delete_raw_also_removes_its_summary_note(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            raw = save_idea(root, "带摘要的想法")
            raw_id = Path(raw["path"]).stem
            note = root / "notes" / "20261105-summary-note.md"
            note.parent.mkdir(parents=True)
            note.write_text(
                "---\n"
                'id: "20261105-summary-note"\n'
                'title: "自动摘要"\n'
                'type: "note"\n'
                'status: "active"\n'
                'created_at: "2026-11-05 16:00"\n'
                'updated_at: "2026-11-05 16:00"\n'
                'source_url: ""\n'
                'source_type: "idea"\n'
                'tags: []\n'
                'topics: []\n'
                'related: []\n'
                f'references: ["{raw_id}"]\n'
                "---\n\n摘要\n",
                encoding="utf-8",
            )
            result = delete_document(root, raw["path"])
            self.assertIn("自动摘要", result["message"])
            self.assertFalse(note.exists())


if __name__ == "__main__":
    unittest.main()
