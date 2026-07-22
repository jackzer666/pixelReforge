"""基于 JSON 的轻量处理状态记录。"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


class JsonStateStore:
    """读取和原子更新 process_state.json。"""

    def __init__(self, path: Path):
        """载入指定 JSON 文件；文件不存在时从空状态开始。"""

        self.path = path
        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        """读取、解析并验证状态文件的顶层结构。"""

        if not self.path.exists():
            return self._empty_state()

        try:
            content = self.path.read_text(encoding="utf-8-sig")
        except OSError as error:
            raise RuntimeError(
                f"无法读取处理记录：{self.path}，原因：{error}"
            ) from error

        # 用户手动清空状态文件时，将空文件或纯空白内容视为全新状态。
        if not content.strip():
            return self._empty_state()

        try:
            data = json.loads(content)
        except json.JSONDecodeError as error:
            raise RuntimeError(
                f"无法读取处理记录：{self.path}，原因：{error}"
            ) from error

        if (
            not isinstance(data, dict)
            or data.get("version") != 1
            or not isinstance(data.get("records"), dict)
            or not all(
                isinstance(task_id, str) and isinstance(record, dict)
                for task_id, record in data["records"].items()
            )
        ):
            raise RuntimeError(f"处理记录格式无效：{self.path}")
        return data

    @staticmethod
    def _empty_state() -> dict[str, Any]:
        """创建当前版本的全新状态数据。"""

        return {"version": 1, "records": {}}

    def _save(self) -> None:
        """先写临时文件再原子替换，降低状态文件损坏风险。"""

        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            temporary.write_text(
                json.dumps(self.data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(temporary, self.path)
        finally:
            if temporary.exists():
                try:
                    temporary.unlink()
                except OSError:
                    pass

    def get(self, task_id: str) -> dict[str, Any] | None:
        """根据任务标识读取一条记录。"""

        return self.data["records"].get(task_id)

    def has_complete_outputs(self, task_id: str) -> bool:
        """判断任务是否成功，且两个输出文件当前仍然存在。"""

        record = self.get(task_id)
        if not record or record.get("status") != "success":
            return False
        outputs = record.get("outputs", [])
        return (
            isinstance(outputs, list)
            and len(outputs) == 2
            and all(isinstance(path, str) and Path(path).is_file() for path in outputs)
        )

    def mark_processing(
        self,
        task_id: str,
        *,
        source: Path,
        source_hash: str,
        parameters: dict[str, object],
    ) -> None:
        """将任务写为处理中，并记录源文件与算法参数。"""

        self.data["records"][task_id] = {
            "source_name": source.name,
            "source_path": str(source),
            "source_hash": source_hash,
            "parameters": parameters,
            "status": "processing",
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "outputs": [],
            "error": None,
        }
        self._save()

    def mark_success(self, task_id: str, outputs: list[Path]) -> None:
        """将任务写为成功，并保存两个输出文件路径。"""

        record = self.data["records"][task_id]
        record.update(
            status="success",
            completed_at=datetime.now().isoformat(timespec="seconds"),
            outputs=[str(path) for path in outputs],
            error=None,
        )
        self._save()

    def mark_failed(self, task_id: str, error: str) -> None:
        """将任务写为失败，并保存可供重试排查的错误信息。"""

        record = self.data["records"][task_id]
        record.update(
            status="failed",
            completed_at=datetime.now().isoformat(timespec="seconds"),
            error=error,
        )
        self._save()
