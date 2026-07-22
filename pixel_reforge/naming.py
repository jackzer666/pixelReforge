"""输出文件命名。"""

from datetime import datetime
from pathlib import Path


def build_output_paths(
    source: Path,
    output_dir: Path,
    scale: int,
    created_at: datetime | None = None,
) -> tuple[Path, Path]:
    """按照“原名_时间_倍数.png”生成两个不会冲突的输出路径。"""

    moment = created_at or datetime.now()
    # 精确到微秒；若指定时间或极端情况下仍重名，则自动追加序号。
    timestamp = moment.strftime("%Y%m%d_%H%M%S_%f")
    counter = 0

    while True:
        unique_time = timestamp if counter == 0 else f"{timestamp}_{counter}"
        base_name = f"{source.stem}_{unique_time}"
        paths = (
            output_dir / f"{base_name}_1x.png",
            output_dir / f"{base_name}_{scale}x.png",
        )
        if not any(path.exists() for path in paths):
            return paths
        counter += 1
