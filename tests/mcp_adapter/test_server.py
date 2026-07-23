"""单工具 FastMCP Server 的边界和结果测试。"""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from mcp.server.fastmcp.exceptions import ToolError

from pixel_reforge.config import AppConfig
from pixel_reforge.mcp_adapter.server import create_server
from pixel_reforge.models import ProcessResult


class FakeWorker:
    """返回固定领域结果，并记录 Server 传入的参数。"""

    def __init__(self, status: str = "success") -> None:
        self.status = status
        self.calls: list[tuple[Path, AppConfig, bool, bool]] = []
        self.closed = False

    async def submit(
        self,
        source: Path,
        config: AppConfig,
        *,
        force: bool = False,
        archive_source: bool = True,
    ) -> ProcessResult:
        self.calls.append((source, config, force, archive_source))
        outputs = (
            [config.output_dir / "result_1x.png", config.output_dir / "result_8x.png"]
            if self.status != "failed"
            else []
        )
        return ProcessResult(
            source=source,
            status=self.status,  # type: ignore[arg-type]
            outputs=outputs,
            error="处理失败" if self.status == "failed" else None,
        )

    async def shutdown(self) -> None:
        self.closed = True


class ServerTests(unittest.IsolatedAsyncioTestCase):
    """验证 Server 只暴露精简方案约定的能力。"""

    def setUp(self) -> None:
        self.temporary = TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.input_dir = self.root / "input"
        self.input_dir.mkdir()
        self.source = self.input_dir / "hero.png"
        self.source.write_bytes(b"test image placeholder")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    async def test_server_lists_exactly_one_write_tool(self) -> None:
        worker = FakeWorker()
        server = create_server(project_root=self.root, worker=worker)

        tools = await server.list_tools()

        self.assertEqual([tool.name for tool in tools], ["reforge_image"])
        tool = tools[0]
        self.assertFalse(tool.annotations.readOnlyHint)
        self.assertEqual(
            set(tool.inputSchema["properties"]),
            {
                "source_path",
                "scale",
                "sample_method",
                "refine_intensity",
                "force",
                "archive_source",
            },
        )
        self.assertEqual(tool.inputSchema["required"], ["source_path"])

    async def test_reforge_image_wraps_existing_process_result(self) -> None:
        worker = FakeWorker()
        server = create_server(project_root=self.root, worker=worker)

        _, structured = await server.call_tool(
            "reforge_image",
            {
                "source_path": "hero.png",
                "scale": 4,
                "sample_method": "majority",
                "refine_intensity": 0.5,
                "force": True,
            },
        )

        self.assertEqual(structured["status"], "success")
        self.assertEqual(structured["source"], str(self.source.resolve()))
        self.assertEqual(len(structured["outputs"]), 2)
        json.dumps(structured)
        source, config, force, archive_source = worker.calls[0]
        self.assertEqual(source, self.source.resolve())
        resolved_root = self.root.resolve()
        self.assertEqual(config.output_dir, resolved_root / "output")
        self.assertEqual(
            config.state_file,
            resolved_root / "data" / "process_state.json",
        )
        self.assertEqual(config.scale, 4)
        self.assertEqual(config.sample_method, "majority")
        self.assertEqual(config.refine_intensity, 0.5)
        self.assertTrue(force)
        self.assertTrue(archive_source)
        self.assertTrue(self.source.exists())

    async def test_archive_source_can_be_disabled_explicitly(self) -> None:
        worker = FakeWorker()
        server = create_server(project_root=self.root, worker=worker)

        await server.call_tool(
            "reforge_image",
            {
                "source_path": "hero.png",
                "archive_source": False,
            },
        )

        self.assertFalse(worker.calls[0][3])

    async def test_failed_domain_result_remains_a_normal_tool_result(self) -> None:
        server = create_server(project_root=self.root, worker=FakeWorker("failed"))

        _, structured = await server.call_tool(
            "reforge_image",
            {"source_path": "hero.png"},
        )

        self.assertEqual(structured["status"], "failed")
        self.assertEqual(structured["outputs"], [])
        self.assertEqual(structured["error"], "处理失败")
        json.dumps(structured)

    async def test_skipped_domain_result_is_json_serializable(self) -> None:
        server = create_server(project_root=self.root, worker=FakeWorker("skipped"))

        _, structured = await server.call_tool(
            "reforge_image",
            {"source_path": "hero.png"},
        )

        self.assertEqual(structured["status"], "skipped")
        self.assertEqual(len(structured["outputs"]), 2)
        self.assertIsNone(structured["error"])
        json.dumps(structured)

    async def test_rejects_absolute_traversal_and_unsupported_paths(self) -> None:
        server = create_server(project_root=self.root, worker=FakeWorker())
        outside = self.root / "outside.png"
        outside.write_bytes(b"outside")
        unsupported = self.input_dir / "notes.txt"
        unsupported.write_text("not an image", encoding="utf-8")

        for source_path in (str(self.source), "../outside.png", "notes.txt", "missing.png"):
            with self.subTest(source_path=source_path):
                with self.assertRaises(ToolError):
                    await server.call_tool(
                        "reforge_image",
                        {"source_path": source_path},
                    )

    async def test_rejects_symlink_source(self) -> None:
        link = self.input_dir / "linked.png"
        try:
            link.symlink_to(self.source)
        except OSError as error:
            self.skipTest(f"当前系统不能创建测试符号链接：{error}")
        server = create_server(project_root=self.root, worker=FakeWorker())

        with self.assertRaises(ToolError):
            await server.call_tool(
                "reforge_image",
                {"source_path": "linked.png"},
            )

    async def test_existing_config_validation_is_exposed_as_tool_error(self) -> None:
        server = create_server(project_root=self.root, worker=FakeWorker())

        with self.assertRaises(ToolError):
            await server.call_tool(
                "reforge_image",
                {"source_path": "hero.png", "scale": 1},
            )


if __name__ == "__main__":
    unittest.main()
