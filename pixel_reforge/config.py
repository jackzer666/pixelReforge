"""应用配置。"""

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


SUPPORTED_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".webp", ".bmp"})

try:
    PERFECT_PIXEL_VERSION = version("perfect-pixel")
except PackageNotFoundError:
    PERFECT_PIXEL_VERSION = "unknown"


@dataclass(frozen=True, slots=True)
class AppConfig:
    """一次处理任务使用的路径和算法参数。"""

    project_dir: Path
    input_dir: Path
    output_dir: Path
    processed_dir: Path
    failed_dir: Path
    state_file: Path
    scale: int = 8
    pixel_mode: str = "detect"
    sample_method: str = "center"
    refine_intensity: float = 0.3
    recursive: bool = False

    def __post_init__(self) -> None:
        """在配置创建时校验算法参数和工作目录。"""

        if self.scale < 2:
            raise ValueError("放大倍数必须大于或等于 2。")
        if self.pixel_mode not in {"detect", "source"}:
            raise ValueError("像素模式只能是 detect 或 source。")
        if self.sample_method not in {"center", "majority"}:
            raise ValueError("取样方式只能是 center 或 majority。")
        if not 0 <= self.refine_intensity <= 1:
            raise ValueError("网格修正强度必须在 0 到 1 之间。")

        working_directories = (
            self.input_dir.resolve(),
            self.output_dir.resolve(),
            self.processed_dir.resolve(),
            self.failed_dir.resolve(),
        )
        if len(set(working_directories)) != len(working_directories):
            raise ValueError("input、output、processed 和 failed 必须是不同目录。")

    @classmethod
    def defaults(cls, project_dir: Path | None = None) -> "AppConfig":
        """以指定项目目录或当前工作目录生成默认配置。"""

        # 默认使用命令执行目录，安装为命令后也不会写入 site-packages。
        root = (project_dir or Path.cwd()).resolve()
        return cls(
            project_dir=root,
            input_dir=root / "input",
            output_dir=root / "output",
            processed_dir=root / "processed",
            failed_dir=root / "failed",
            state_file=root / "data" / "process_state.json",
        )

    def ensure_directories(self) -> None:
        """创建运行所需目录。"""

        for directory in (
            self.input_dir,
            self.output_dir,
            self.processed_dir,
            self.failed_dir,
            self.state_file.parent,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def processing_parameters(self) -> dict[str, object]:
        """返回会影响处理结果的参数，用于生成任务指纹。"""

        # 算法或依赖版本改变时应产生新任务，避免错误复用旧输出。
        return {
            "processor_version": 1,
            "perfect_pixel_version": PERFECT_PIXEL_VERSION,
            "pixel_mode": self.pixel_mode,
            "sample_method": self.sample_method,
            "refine_intensity": self.refine_intensity,
            "scale": self.scale,
        }
