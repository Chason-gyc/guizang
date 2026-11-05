import os
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from model_provider import call_model


class ProviderErrorsTest(unittest.TestCase):
    def test_network_and_response_errors_are_distinct(self):
        with patch.dict(os.environ, {'DASHSCOPE_API_KEY': 'private-test-key'}):
            with patch('urllib.request.urlopen', side_effect=urllib.error.URLError(FileNotFoundError(2, 'missing'))):
                with self.assertRaisesRegex(ValueError, 'HTTPS 连接未建立'):
                    call_model('bailian', 'qwen-plus', 'system', 'input')
            with patch('urllib.request.urlopen') as request:
                request.return_value.__enter__.return_value.read.return_value = b'{}'
                with self.assertRaisesRegex(ValueError, '返回格式异常'):
                    call_model('bailian', 'qwen-plus', 'system', 'input')
