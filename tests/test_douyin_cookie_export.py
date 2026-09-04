import unittest
from types import SimpleNamespace

from scripts.export_douyin_cookies import is_douyin_cookie


class DouyinCookieExportTests(unittest.TestCase):
    def test_only_douyin_domains_are_allowed(self):
        self.assertTrue(is_douyin_cookie(SimpleNamespace(domain=".douyin.com")))
        self.assertTrue(is_douyin_cookie(SimpleNamespace(domain="www.douyin.com")))
        self.assertTrue(is_douyin_cookie(SimpleNamespace(domain=".iesdouyin.com")))
        self.assertFalse(is_douyin_cookie(SimpleNamespace(domain="facebook.com")))
        self.assertFalse(is_douyin_cookie(SimpleNamespace(domain="evildouyin.com")))


if __name__ == "__main__":
    unittest.main()
