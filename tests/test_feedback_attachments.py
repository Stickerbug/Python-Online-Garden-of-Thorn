# -*- coding: utf-8 -*-
"""#235/#242 冒烟测试：附件校验 + 触控双击设置。"""
import os
import sys
import unittest

sys.path.insert(0, '.')

import db


class FeedbackAttachmentTests(unittest.TestCase):
    def setUp(self):
        import feedback_attachments as fa
        self.fa = fa
        self.temp_dir = os.environ.get('GTN_FEEDBACK_ATTACHMENTS_DIR') or ''
        test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tmp_att')
        os.environ['GTN_FEEDBACK_ATTACHMENTS_DIR'] = test_dir
        os.makedirs(test_dir, exist_ok=True)

    def tearDown(self):
        import shutil
        test_dir = os.environ.get('GTN_FEEDBACK_ATTACHMENTS_DIR', '')
        if 'tmp_att' in test_dir:
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_sniff_and_size_limit(self):
        png = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        self.assertEqual(self.fa.sniff_image_type(png), 'image/png')
        jpeg = b'\xff\xd8\xff' + b'\x00' * 50
        self.assertEqual(self.fa.sniff_image_type(jpeg), 'image/jpeg')
        webp = b'RIFF\x00\x00\x00\x00WEBP' + b'\x00' * 10
        self.assertEqual(self.fa.sniff_image_type(webp), 'image/webp')
        self.assertIsNone(self.fa.sniff_image_type(b'<script>evil</script>'))
        self.assertIsNone(self.fa.sniff_image_type(b'\x89PNG\r\n\x1a\n' + b'\x00' * (300 * 1024)))

    def test_save_and_serve_token(self):
        png = b'\x89PNG\r\n\x1a\n' + b'\x00' * 200
        aid, url = self.fa.save_attachment(1, png)
        self.assertTrue(url.startswith('/feedback-attachments/'))
        token = url.rsplit('/', 1)[1]
        result = self.fa.open_attachment_file(token)
        self.assertIsNotNone(result)
        path, mime = result
        self.assertEqual(mime, 'image/png')
        self.assertIsNone(self.fa.open_attachment_file('../etc/passwd'))
        self.assertIsNone(self.fa.open_attachment_file('x' * 100))


if __name__ == '__main__':
    unittest.main()
