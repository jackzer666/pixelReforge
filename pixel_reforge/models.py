"""处理流程使用的数据模型。"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import numpy as np


ProcessStatus = Literal["success", "failed", "skipped"]


@dataclass(slots=True)
class ProcessedImage:
    """单图算法生成的网格尺寸、原始像素图和放大图。"""

    width: int
    height: int
    original: np.ndarray
    scaled: np.ndarray


@dataclass(slots=True)
class ProcessResult:
    """一张源图片在工作流中的最终处理结果。"""

    source: Path
    status: ProcessStatus
    outputs: list[Path] = field(default_factory=list)
    error: str | None = None


@dataclass(slots=True)
class BatchResult:
    """批处理结果集合，并提供按状态统计的便捷方法。"""

    results: list[ProcessResult] = field(default_factory=list)

    def add(self, result: ProcessResult) -> None:
        """向批次中追加一张图片的处理结果。"""

        self.results.append(result)

    def count(self, status: ProcessStatus) -> int:
        """统计指定状态的图片数量。"""

        return sum(result.status == status for result in self.results)

    @property
    def total(self) -> int:
        """返回本批次扫描到的图片总数。"""

        return len(self.results)
