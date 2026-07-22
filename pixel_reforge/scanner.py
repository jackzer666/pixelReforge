"""扫描输入目录并筛选可以安全处理的图片文件。"""

from collections.abc import Iterable
from pathlib import Path

from .config import SUPPORTED_EXTENSIONS


def is_supported_image(path: Path) -> bool:
    """判断路径是否为受支持且非符号链接的普通图片文件。"""

    # 不跟随符号链接，避免批量归档时移动输入目录之外的真实文件。
    return not path.is_symlink() and path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS


def _is_inside_any(path: Path, directories: tuple[Path, ...]) -> bool:
    """判断路径是否位于任意排除目录之内。"""

    for directory in directories:
        try:
            path.relative_to(directory)
            return True
        except ValueError:
            continue
    return False


def scan_images(
    directory: Path,
    recursive: bool = False,
    excluded_directories: Iterable[Path] = (),
) -> list[Path]:
    """扫描目录，排除托管目录后返回按路径排序的图片。"""

    if not directory.exists():
        return []

    excluded = tuple(path.resolve() for path in excluded_directories)
    # 非递归模式只看当前层；递归模式会遍历所有子目录。
    candidates: Iterable[Path] = directory.rglob("*") if recursive else directory.iterdir()
    images: list[Path] = []
    for path in candidates:
        if not is_supported_image(path):
            continue
        resolved = path.resolve()
        if not _is_inside_any(resolved, excluded):
            images.append(resolved)

    return sorted(images, key=lambda path: str(path).lower())
