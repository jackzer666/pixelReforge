"""单工作子进程的串行和 stdout 隔离测试。"""

import asyncio
import subprocess
import sys
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from pixel_reforge.config import AppConfig
from pixel_reforge.mcp_adapter.worker import ReforgeWorker
from pixel_reforge.models import ProcessResult


def recording_worker(
    source: Path,
    config: AppConfig,
    force: bool,
    archive_source: bool,
) -> ProcessResult:
    """记录开始和结束顺序，供 spawn 子进程测试调用。"""

    label = "second" if force else "first"
    with source.open("a", encoding="utf-8") as stream:
        stream.write(f"start:{label}\n")
    time.sleep(0.15)
    with source.open("a", encoding="utf-8") as stream:
        stream.write(f"end:{label}\n")
    return ProcessResult(source=source, status="success")


def printing_worker(
    source: Path,
    config: AppConfig,
    force: bool,
    archive_source: bool,
) -> ProcessResult:
    """模拟第三方依赖直接向 stdout 输出。"""

    print("THIRD_PARTY_STDOUT", flush=True)
    return ProcessResult(source=source, status="success")


class WorkerTests(unittest.IsolatedAsyncioTestCase):
    """验证精简执行器的两个必要保证。"""

    async def test_two_submissions_run_serially(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            record = root / "order.txt"
            config = AppConfig.defaults(root)
            worker = ReforgeWorker(worker_function=recording_worker)
            try:
                await asyncio.gather(
                    worker.submit(record, config, force=False),
                    worker.submit(record, config, force=True),
                )
            finally:
                await worker.shutdown()

            self.assertEqual(
                record.read_text(encoding="utf-8").splitlines(),
                ["start:first", "end:first", "start:second", "end:second"],
            )

    def test_child_stdout_is_redirected_away_from_parent_stdout(self) -> None:
        script = """
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from pixel_reforge.config import AppConfig
from pixel_reforge.mcp_adapter.worker import ReforgeWorker
from tests.mcp_adapter.test_worker import printing_worker

async def run():
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        worker = ReforgeWorker(worker_function=printing_worker)
        try:
            await worker.submit(root / "source.png", AppConfig.defaults(root))
        finally:
            await worker.shutdown()
    print("PARENT_STDOUT", flush=True)

asyncio.run(run())
"""
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=Path(__file__).parents[2],
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )

        self.assertEqual(completed.stdout.strip(), "PARENT_STDOUT")
        self.assertIn("THIRD_PARTY_STDOUT", completed.stderr)


if __name__ == "__main__":
    unittest.main()
