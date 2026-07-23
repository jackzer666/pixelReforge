"""真实 STDIO 进程中的最小 MCP 冒烟测试。"""

import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import cv2
import numpy as np
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _write_detectable_pixel_image(path: Path) -> None:
    """生成 perfect-pixel 可以稳定识别的 16×16 随机色块图。"""

    random = np.random.default_rng(42)
    channel = random.integers(0, 5, (16, 16), dtype=np.uint8) * 60
    pixel_art = np.stack(
        [channel, np.roll(channel, 1, axis=0), np.roll(channel, 1, axis=1)],
        axis=2,
    )
    enlarged = cv2.resize(
        pixel_art,
        (64, 64),
        interpolation=cv2.INTER_NEAREST,
    )
    if not cv2.imwrite(str(path), enlarged):
        raise OSError(f"无法创建测试图片：{path}")


class StdioTests(unittest.IsolatedAsyncioTestCase):
    """证明实际协议进程能在算法调用前后继续收发消息。"""

    async def test_real_stdio_server_processes_one_image(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_dir = root / "input"
            input_dir.mkdir()
            source = input_dir / "pixel-art.png"
            _write_detectable_pixel_image(source)
            environment = os.environ.copy()
            environment["PIXEL_REFORGE_ROOT"] = str(root)

            parameters = StdioServerParameters(
                command=sys.executable,
                args=["-m", "pixel_reforge.mcp_adapter.server"],
                env=environment,
                cwd=Path(__file__).parents[2],
            )
            async with stdio_client(parameters) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    before = await session.list_tools()
                    result = await session.call_tool(
                        "reforge_image",
                        {
                            "source_path": "pixel-art.png",
                            "scale": 2,
                            "pixel_mode": "source",
                        },
                    )
                    after = await session.list_tools()

            self.assertFalse(result.isError)
            self.assertEqual(result.structuredContent["status"], "success")
            self.assertEqual(len(result.structuredContent["outputs"]), 2)
            self.assertFalse(source.exists())
            self.assertTrue((root / "processed" / source.name).is_file())
            output_paths = [
                Path(output) for output in result.structuredContent["outputs"]
            ]
            for output in output_paths:
                self.assertTrue(output.is_file())
            original = cv2.imread(str(output_paths[0]))
            preview = cv2.imread(str(output_paths[1]))
            self.assertIsNotNone(original)
            self.assertIsNotNone(preview)
            self.assertEqual(original.shape[:2], (64, 64))
            self.assertEqual(preview.shape[:2], (128, 128))
            self.assertEqual([tool.name for tool in before.tools], ["reforge_image"])
            self.assertEqual([tool.name for tool in after.tools], ["reforge_image"])


if __name__ == "__main__":
    unittest.main()
