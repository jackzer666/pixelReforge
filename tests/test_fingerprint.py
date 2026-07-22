"""文件内容指纹与任务标识测试。"""

import tempfile
import unittest
from pathlib import Path

from pixel_reforge.fingerprint import build_task_id, calculate_sha256


class FingerprintTests(unittest.TestCase):
    """验证内容去重与参数变化识别。"""

    def test_same_content_has_same_hash_and_parameter_change_has_new_task_id(self) -> None:
        """同内容应同哈希，而不同参数应生成不同任务标识。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first.png"
            second = root / "second.jpg"
            first.write_bytes(b"same image content")
            second.write_bytes(b"same image content")

            first_hash = calculate_sha256(first)
            second_hash = calculate_sha256(second)

            self.assertEqual(first_hash, second_hash)
            self.assertNotEqual(
                build_task_id(first_hash, {"scale": 8}),
                build_task_id(second_hash, {"scale": 16}),
            )


if __name__ == "__main__":
    unittest.main()
