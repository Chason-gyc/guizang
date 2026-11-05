import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from web_service import fetch_webpage


class BrowserFallbackTest(unittest.TestCase):
    def test_521_uses_browser(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("https://example.com", 521, "", {}, None)), patch("browser_reader.fetch_rendered_page", return_value=("Article", "Body")) as browser:
            self.assertEqual(fetch_webpage("https://example.com"), ("Article", "Body"))
            browser.assert_called_once_with("https://example.com")

    def test_404_does_not_launch_browser(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("https://example.com", 404, "", {}, None)), patch("browser_reader.fetch_rendered_page") as browser:
            with self.assertRaisesRegex(ValueError, "404"):
                fetch_webpage("https://example.com")
            browser.assert_not_called()
