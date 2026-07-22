"""应用配置校验测试。"""

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from pixel_reforge.config import AppConfig


class ConfigTests(unittest.TestCase):
    """验证非法配置会被及时拒绝。"""

    def test_working_directories_must_be_different(self) -> None:
        """输入、输出、成功和失败目录不能指向同一位置。"""

        with tempfile.TemporaryDirectory() as temporary:
            config = AppConfig.defaults(Path(temporary))

            with self.assertRaisesRegex(ValueError, "必须是不同目录"):
                replace(config, output_dir=config.input_dir)

    def test_scale_must_be_at_least_two(self) -> None:
        """放大图倍数至少为 2。"""

        with tempfile.TemporaryDirectory() as temporary:
            config = AppConfig.defaults(Path(temporary))

            with self.assertRaisesRegex(ValueError, "大于或等于 2"):
                replace(config, scale=1)

    def test_processing_parameters_include_dependency_version(self) -> None:
        """任务指纹参数必须包含 perfect-pixel 版本。"""

        with tempfile.TemporaryDirectory() as temporary:
            config = AppConfig.defaults(Path(temporary))

            self.assertIn("perfect_pixel_version", config.processing_parameters())


if __name__ == "__main__":
    unittest.main()
