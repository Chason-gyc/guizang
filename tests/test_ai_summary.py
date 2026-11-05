import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from ai_summary import summarize
from ingest import create_raw_document
from knowledge import validate_documents


class SummaryTest(unittest.TestCase):
    def test_summary_preserves_source_and_creates_valid_note(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = create_raw_document(root=root, title="想法", source_type="idea", content="知识应该帮助创作")
            original = path.read_bytes()
            with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test"}), patch("urllib.request.urlopen") as call:
                call.return_value.__enter__.return_value.read.return_value = b'{"choices":[{"finish_reason":"stop","message":{"content":"Summary"}}]}'
                result = summarize(root, path.relative_to(root).as_posix(), "qwen-plus")
            self.assertTrue((root / result["path"]).exists())
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(validate_documents(root), [])

    def test_invalid_path_and_model_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                summarize(Path(folder), "../outside.md", "qwen-plus")
            with self.assertRaises(ValueError):
                summarize(Path(folder), "raw/test.md", "")
