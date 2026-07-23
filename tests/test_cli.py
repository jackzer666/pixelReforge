"""命令行参数测试。"""

import unittest

from pixel_reforge.cli import build_parser


class CliTests(unittest.TestCase):
    """验证 CLI 的公共参数约定。"""

    def test_pixel_mode_defaults_to_detect(self) -> None:
        """省略像素模式时必须使用自动检测。"""

        arguments = build_parser().parse_args([])

        self.assertEqual(arguments.pixel_mode, "detect")


if __name__ == "__main__":
    unittest.main()
