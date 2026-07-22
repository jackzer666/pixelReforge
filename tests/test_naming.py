"""输出图片命名规则测试。"""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from pixel_reforge.naming import build_output_paths


class NamingTests(unittest.TestCase):
    """验证时间、倍数和重名序号的组合规则。"""

    def test_build_output_paths_uses_source_time_and_scale(self) -> None:
        """输出名应包含原名、时间和倍数。"""

        original, scaled = build_output_paths(
            Path("earth.jpg"),
            Path("output"),
            8,
            datetime(2026, 7, 22, 12, 30, 45, 123456),
        )

        self.assertEqual(original, Path("output/earth_20260722_123045_123456_1x.png"))
        self.assertEqual(scaled, Path("output/earth_20260722_123045_123456_8x.png"))

    def test_existing_names_get_a_sequence_suffix(self) -> None:
        """目标文件已存在时应追加序号而不是覆盖。"""

        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary)
            moment = datetime(2026, 7, 22, 12, 30, 45, 123456)
            first_original, first_scaled = build_output_paths(
                Path("earth.jpg"), output_dir, 8, moment
            )
            first_original.touch()
            first_scaled.touch()

            original, scaled = build_output_paths(Path("earth.jpg"), output_dir, 8, moment)

            self.assertEqual(original.name, "earth_20260722_123045_123456_1_1x.png")
            self.assertEqual(scaled.name, "earth_20260722_123045_123456_1_8x.png")


if __name__ == "__main__":
    unittest.main()
