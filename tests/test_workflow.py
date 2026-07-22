"""单图和批量业务流程测试。"""

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import numpy as np

from pixel_reforge.config import AppConfig
from pixel_reforge.models import ProcessedImage, ProcessResult
from pixel_reforge.state import JsonStateStore
from pixel_reforge.workflow import process_batch, process_one


class WorkflowTests(unittest.TestCase):
    """验证成功、去重、失败隔离和批量容错。"""

    def _config(self, root: Path) -> AppConfig:
        """为单个测试创建互不干扰的临时配置。"""

        config = AppConfig.defaults(root)
        config.ensure_directories()
        return replace(config, scale=8)

    @patch("pixel_reforge.workflow.process_image")
    def test_success_archives_source_and_duplicate_is_skipped(self, mock_process) -> None:
        """成功原图应归档，同内容图片再次出现时应复用结果。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = self._config(root)
            source = config.input_dir / "earth.png"
            source.write_bytes(b"same image content")
            mock_process.return_value = ProcessedImage(
                width=2,
                height=2,
                original=np.zeros((2, 2, 3), dtype=np.uint8),
                scaled=np.zeros((16, 16, 3), dtype=np.uint8),
            )

            first = process_one(source, config, archive_source=True)

            self.assertEqual(first.status, "success")
            self.assertFalse(source.exists())
            self.assertTrue((config.processed_dir / "earth.png").exists())
            self.assertTrue(all(path.exists() for path in first.outputs))

            duplicate = config.input_dir / "duplicate.png"
            duplicate.write_bytes(b"same image content")
            second = process_one(duplicate, config, archive_source=True)

            self.assertEqual(second.status, "skipped")
            self.assertFalse(duplicate.exists())
            self.assertEqual(mock_process.call_count, 1)

    @patch("pixel_reforge.workflow.process_image", side_effect=RuntimeError("测试失败"))
    def test_failure_moves_source_to_failed_directory(self, mock_process) -> None:
        """算法失败时应记录失败并隔离原图。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = self._config(root)
            source = config.input_dir / "broken.png"
            source.write_bytes(b"broken")

            result = process_one(source, config, archive_source=True)

            self.assertEqual(result.status, "failed")
            self.assertFalse(source.exists())
            self.assertTrue((config.failed_dir / "broken.png").exists())

    @patch("pixel_reforge.workflow._move_source", side_effect=OSError("没有移动权限"))
    @patch("pixel_reforge.workflow.process_image")
    def test_archive_failure_does_not_change_success_to_failure(
        self,
        mock_process,
        mock_move,
    ) -> None:
        """归档异常不能推翻已经成功生成并记录的处理结果。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = self._config(root)
            source = config.input_dir / "earth.png"
            source.write_bytes(b"image")
            mock_process.return_value = ProcessedImage(
                width=2,
                height=2,
                original=np.zeros((2, 2, 3), dtype=np.uint8),
                scaled=np.zeros((16, 16, 3), dtype=np.uint8),
            )

            result = process_one(source, config, archive_source=True)

            self.assertEqual(result.status, "success")
            self.assertTrue(source.exists())
            self.assertTrue(all(path.exists() for path in result.outputs))
            state = JsonStateStore(config.state_file)
            self.assertEqual(next(iter(state.data["records"].values()))["status"], "success")

    @patch("pixel_reforge.workflow.process_image")
    def test_recursive_batch_does_not_process_generated_directories(self, mock_process) -> None:
        """递归批处理不得把既有输出当作新输入。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = replace(AppConfig.defaults(root), input_dir=root, recursive=True)
            config.ensure_directories()
            (root / "source.png").write_bytes(b"source")
            (config.output_dir / "old-output.png").write_bytes(b"generated")
            mock_process.return_value = ProcessedImage(
                width=2,
                height=2,
                original=np.zeros((2, 2, 3), dtype=np.uint8),
                scaled=np.zeros((16, 16, 3), dtype=np.uint8),
            )

            result = process_batch(config)

            self.assertEqual(result.total, 1)
            self.assertEqual(result.count("success"), 1)
            self.assertEqual(mock_process.call_count, 1)

    @patch("pixel_reforge.workflow.calculate_sha256", side_effect=OSError("无法读取"))
    def test_hash_failure_moves_source_to_failed_directory(self, mock_hash) -> None:
        """无法计算指纹时也应隔离原图并继续批次。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = self._config(root)
            source = config.input_dir / "unreadable.png"
            source.write_bytes(b"image")

            result = process_one(source, config, archive_source=True)

            self.assertEqual(result.status, "failed")
            self.assertFalse(source.exists())
            self.assertTrue((config.failed_dir / "unreadable.png").exists())

    @patch("pixel_reforge.workflow.process_one")
    def test_unexpected_error_does_not_stop_batch(self, mock_process_one) -> None:
        """单项未预期异常不应阻止下一张图片处理。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = self._config(root)
            first = config.input_dir / "a.png"
            second = config.input_dir / "b.png"
            first.write_bytes(b"first")
            second.write_bytes(b"second")
            mock_process_one.side_effect = [
                RuntimeError("意外错误"),
                ProcessResult(source=second, status="success"),
            ]

            result = process_batch(config)

            self.assertEqual(result.total, 2)
            self.assertEqual(result.count("failed"), 1)
            self.assertEqual(result.count("success"), 1)


if __name__ == "__main__":
    unittest.main()
