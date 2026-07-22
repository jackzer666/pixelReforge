"""输入目录扫描和过滤规则测试。"""

import tempfile
import unittest
from pathlib import Path

from pixel_reforge.scanner import scan_images


class ScannerTests(unittest.TestCase):
    """验证图片格式、递归和排除目录行为。"""

    def test_scan_images_filters_extensions_and_supports_recursion(self) -> None:
        """扫描时只返回支持的图片，并按配置决定是否递归。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "b.JPG").write_bytes(b"image")
            (root / "a.png").write_bytes(b"image")
            (root / "notes.txt").write_text("ignore", encoding="utf-8")
            nested = root / "nested"
            nested.mkdir()
            (nested / "c.webp").write_bytes(b"image")

            direct = scan_images(root)
            recursive = scan_images(root, recursive=True)

            self.assertEqual([path.name for path in direct], ["a.png", "b.JPG"])
            self.assertEqual([path.name for path in recursive], ["a.png", "b.JPG", "c.webp"])

    def test_recursive_scan_ignores_managed_directories(self) -> None:
        """递归扫描不得重新读取输出目录中的生成图片。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            output.mkdir()
            (root / "source.png").write_bytes(b"source")
            (output / "generated.png").write_bytes(b"generated")

            images = scan_images(root, recursive=True, excluded_directories=[output])

            self.assertEqual([path.name for path in images], ["source.png"])


if __name__ == "__main__":
    unittest.main()
