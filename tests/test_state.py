"""JSON 状态文件读取、写入和完整性判断测试。"""

import tempfile
import unittest
from pathlib import Path

from pixel_reforge.state import JsonStateStore


class StateTests(unittest.TestCase):
    """验证空状态、成功状态和异常结构。"""

    def test_empty_file_is_treated_as_new_state(self) -> None:
        """完全空白的状态文件应被视为新状态。"""

        with tempfile.TemporaryDirectory() as temporary:
            state_path = Path(temporary) / "state.json"
            state_path.write_text("", encoding="utf-8")

            state = JsonStateStore(state_path)

            self.assertEqual(state.data, {"version": 1, "records": {}})

    def test_whitespace_only_file_is_treated_as_new_state(self) -> None:
        """只包含空白字符的状态文件也应被视为新状态。"""

        with tempfile.TemporaryDirectory() as temporary:
            state_path = Path(temporary) / "state.json"
            state_path.write_text("  \n\t", encoding="utf-8")

            state = JsonStateStore(state_path)

            self.assertEqual(state.data, {"version": 1, "records": {}})

    def test_success_requires_output_files_to_exist(self) -> None:
        """成功记录只有在两个输出文件都存在时才完整。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state_path = root / "data" / "state.json"
            original = root / "output_1x.png"
            scaled = root / "output_8x.png"
            original.write_bytes(b"image")
            scaled.write_bytes(b"image")

            state = JsonStateStore(state_path)
            state.mark_processing(
                "task",
                source=root / "input.png",
                source_hash="abc",
                parameters={"scale": 8},
            )
            state.mark_success("task", [original, scaled])

            reloaded = JsonStateStore(state_path)
            self.assertTrue(reloaded.has_complete_outputs("task"))
            scaled.unlink()
            self.assertFalse(reloaded.has_complete_outputs("task"))

    def test_invalid_output_list_is_not_considered_complete(self) -> None:
        """输出路径字段不是列表时不得复用该记录。"""

        with tempfile.TemporaryDirectory() as temporary:
            state = JsonStateStore(Path(temporary) / "state.json")
            state.data["records"]["task"] = {
                "status": "success",
                "outputs": "not-a-list",
            }

            self.assertFalse(state.has_complete_outputs("task"))


if __name__ == "__main__":
    unittest.main()
