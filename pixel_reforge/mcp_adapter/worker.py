"""在独立进程中串行执行 MCP 图片处理任务。"""

from __future__ import annotations

import asyncio
import os
import sys
import threading
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from multiprocessing.context import BaseContext
from pathlib import Path
from typing import Callable

from pixel_reforge.config import AppConfig
from pixel_reforge.models import ProcessResult
from pixel_reforge.workflow import process_one


WorkerFunction = Callable[[Path, AppConfig, bool, bool], ProcessResult]


class WorkerClosedError(RuntimeError):
    """工作进程已经关闭。"""


def _redirect_stdout_to_stderr() -> None:
    """让子进程的普通输出无法写入 MCP 主进程的协议 stdout。"""

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except (AttributeError, OSError, ValueError):
            pass
    os.dup2(2, 1)


def _run_reforge(
    source: Path,
    config: AppConfig,
    force: bool,
    archive_source: bool,
) -> ProcessResult:
    """调用现有 Python 工作流，并按调用参数决定是否归档原图。"""

    return process_one(
        source,
        config,
        force=force,
        archive_source=archive_source,
    )


class ReforgeWorker:
    """惰性创建一个工作子进程，并按提交顺序执行写任务。"""

    def __init__(
        self,
        *,
        mp_context: BaseContext | None = None,
        worker_function: WorkerFunction = _run_reforge,
    ) -> None:
        self._mp_context = mp_context or get_context("spawn")
        self._worker_function = worker_function
        self._executor: ProcessPoolExecutor | None = None
        self._lock = threading.Lock()
        self._closed = False

    def _get_executor(self) -> ProcessPoolExecutor:
        with self._lock:
            if self._closed:
                raise WorkerClosedError("PixelReforge MCP 工作进程已关闭。")
            if self._executor is None:
                self._executor = ProcessPoolExecutor(
                    max_workers=1,
                    mp_context=self._mp_context,
                    initializer=_redirect_stdout_to_stderr,
                )
            return self._executor

    async def submit(
        self,
        source: Path,
        config: AppConfig,
        *,
        force: bool = False,
        archive_source: bool = True,
    ) -> ProcessResult:
        """提交一次处理；取消等待不强制终止已经开始的底层任务。"""

        future = self._get_executor().submit(
            self._worker_function,
            source,
            config,
            force,
            archive_source,
        )
        return await asyncio.shield(asyncio.wrap_future(future))

    async def shutdown(self) -> None:
        """停止接收任务，并等待已经提交的工作结束。"""

        with self._lock:
            if self._closed:
                return
            self._closed = True
            executor = self._executor

        if executor is not None:
            await asyncio.to_thread(
                executor.shutdown,
                wait=True,
                cancel_futures=False,
            )
