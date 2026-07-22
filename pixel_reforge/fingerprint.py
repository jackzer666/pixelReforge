"""图片和处理任务指纹。"""

import hashlib
import json
from pathlib import Path


def calculate_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """分块计算文件 SHA-256，避免一次加载整个文件。"""

    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def build_task_id(source_hash: str, parameters: dict[str, object]) -> str:
    """将原图内容和算法参数组合为稳定的任务标识。"""

    payload = json.dumps(parameters, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{source_hash}:{payload}".encode("utf-8")).hexdigest()

