"""只暴露单图重铸工具的本地 STDIO MCP Server。"""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import replace
from pathlib import Path
from typing import Any, Literal, Protocol

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from pixel_reforge.config import AppConfig, SUPPORTED_EXTENSIONS
from pixel_reforge.models import ProcessResult

from .worker import ReforgeWorker


LOGGER = logging.getLogger(__name__)


class Worker(Protocol):
    """Server 所需的最小工作进程接口，便于测试替换。"""

    async def submit(
        self,
        source: Path,
        config: AppConfig,
        *,
        force: bool = False,
        archive_source: bool = True,
    ) -> ProcessResult:
        """提交一次单图处理。"""

    async def shutdown(self) -> None:
        """关闭工作进程。"""


def _project_root(value: str | Path | None = None) -> Path:
    """解析并验证 Server 固定使用的项目根目录。"""

    raw = Path(
        value
        if value is not None
        else os.environ.get("PIXEL_REFORGE_ROOT", os.getcwd())
    ).expanduser()
    if not raw.is_absolute():
        raw = Path.cwd() / raw
    try:
        root = raw.resolve(strict=True)
    except OSError as error:
        raise RuntimeError(f"PixelReforge 项目根目录不存在或不可访问：{raw}") from error
    if not root.is_dir():
        raise RuntimeError(f"PixelReforge 项目根路径不是目录：{root}")
    if raw.is_symlink():
        raise RuntimeError("PixelReforge 项目根目录不能是符号链接。")
    return root


def _validate_source(project_root: Path, source_path: str) -> Path:
    """只接受项目 input 目录内的相对、非符号链接图片。"""

    if not source_path.strip():
        raise ToolError("source_path 不能为空。")

    relative = Path(source_path).expanduser()
    if relative.is_absolute():
        raise ToolError("source_path 必须是相对于项目 input 目录的路径。")
    if ".." in relative.parts:
        raise ToolError("source_path 不能包含 '..'。")

    input_root = project_root / "input"
    if input_root.is_symlink():
        raise ToolError("项目 input 目录不能是符号链接。")

    candidate = input_root / relative
    current = input_root
    for component in relative.parts:
        current = current / component
        if current.is_symlink():
            raise ToolError("source_path 不能包含符号链接。")

    try:
        resolved_input = input_root.resolve(strict=True)
        source = candidate.resolve(strict=True)
    except OSError as error:
        raise ToolError("输入图片不存在或不可访问。") from error

    try:
        source.relative_to(resolved_input)
    except ValueError as error:
        raise ToolError("输入图片必须位于项目 input 目录内。") from error
    if not source.is_file():
        raise ToolError("source_path 必须指向普通文件。")
    if source.suffix.lower() not in SUPPORTED_EXTENSIONS:
        supported = "、".join(sorted(SUPPORTED_EXTENSIONS))
        raise ToolError(f"不支持的图片格式；支持：{supported}。")
    return source


def _serialize_result(result: ProcessResult) -> dict[str, Any]:
    """把现有领域结果转换为 MCP 可返回的 JSON 基础类型。"""

    return {
        "source": str(result.source),
        "status": result.status,
        "outputs": [str(path) for path in result.outputs],
        "error": result.error,
    }


def create_server(
    *,
    project_root: str | Path | None = None,
    worker: Worker | None = None,
) -> FastMCP:
    """创建一个只包含 `reforge_image` 的 FastMCP Server。"""

    root = _project_root(project_root)
    reforge_worker = worker or ReforgeWorker()

    @asynccontextmanager
    async def lifespan(_server: FastMCP[Any]) -> AsyncIterator[None]:
        try:
            yield
        finally:
            await reforge_worker.shutdown()

    server = FastMCP(
        "pixel-reforge",
        instructions=(
            "处理 PixelReforge 项目 input 目录中的单张图片。"
            "工具会写入 output 和状态文件，并默认按处理结果归档原图。"
        ),
        log_level="WARNING",
        lifespan=lifespan,
    )

    @server.tool(
        name="reforge_image",
        description=(
            "重铸 input 目录中的一张图片，生成原始像素图和放大预览图。"
            "pixel_mode=detect 时自动检测逻辑像素网格；pixel_mode=source 时"
            "将每个输入像素直接作为一个 1×1 逻辑像素。"
            "该工具会写入 output 目录和处理状态；archive_source=true 时会"
            "把成功原图移动到 processed，或把失败原图移动到 failed。"
        ),
        annotations=ToolAnnotations(
            title="重铸单张像素图",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    async def reforge_image(
        source_path: str,
        scale: int = 8,
        pixel_mode: Literal["detect", "source"] = "detect",
        sample_method: Literal["center", "majority"] = "center",
        refine_intensity: float = 0.3,
        force: bool = False,
        archive_source: bool = True,
    ) -> dict[str, Any]:
        """调用现有单图工作流，并返回其精简结果。"""

        source = _validate_source(root, source_path)
        try:
            config = replace(
                AppConfig.defaults(root),
                scale=scale,
                pixel_mode=pixel_mode,
                sample_method=sample_method,
                refine_intensity=refine_intensity,
            )
        except ValueError as error:
            raise ToolError(str(error)) from error

        try:
            result = await reforge_worker.submit(
                source,
                config,
                force=force,
                archive_source=archive_source,
            )
        except ToolError:
            raise
        except Exception as error:
            LOGGER.exception("PixelReforge 工作进程调用失败")
            raise ToolError(f"无法执行图片重铸：{error}") from error
        return _serialize_result(result)

    return server


def main() -> None:
    """运行本地 STDIO MCP Server。"""

    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
        force=True,
    )
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
