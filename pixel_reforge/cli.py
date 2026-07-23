"""命令行入口。"""

import argparse
import logging
import sys
from dataclasses import replace
from pathlib import Path
from time import monotonic

from .config import AppConfig
from .models import BatchResult
from .workflow import process_batch, process_one


def _positive_scale(value: str) -> int:
    """将命令行字符串转换为合法的图片放大倍数。"""

    scale = int(value)
    if scale < 2:
        raise argparse.ArgumentTypeError("放大倍数必须大于或等于 2")
    return scale


def build_parser() -> argparse.ArgumentParser:
    """创建并配置命令行参数解析器。"""

    parser = argparse.ArgumentParser(description="批量生成规整像素图")
    # 三种输入模式互斥，避免同一次运行无法判断应处理哪个来源。
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument("--file", type=Path, help="只处理一张图片")
    source_group.add_argument("--input-dir", type=Path, help="批量处理指定目录")
    source_group.add_argument(
        "--retry-failed",
        action="store_true",
        help="重新处理 failed 目录中的图片",
    )
    parser.add_argument("--output-dir", type=Path, help="指定输出目录")
    parser.add_argument("--scale", type=_positive_scale, default=8, help="预览图放大倍数")
    parser.add_argument(
        "--pixel-mode",
        choices=("detect", "source"),
        default="detect",
        help="像素模式：detect 自动检测网格，source 将输入像素按 1×1 使用",
    )
    parser.add_argument("--force", action="store_true", help="强制重新处理")
    parser.add_argument("--recursive", action="store_true", help="递归扫描子目录")
    return parser


def _resolve_user_path(path: Path) -> Path:
    """展开用户目录符号并返回绝对路径。"""

    return path.expanduser().resolve()


def _is_inside(path: Path, directory: Path) -> bool:
    """判断文件是否位于指定目录或其子目录中。"""

    return path.resolve().is_relative_to(directory.resolve())


def _print_summary(result: BatchResult, elapsed: float, output_dir: Path) -> None:
    """用中文输出本次运行的数量、耗时和输出目录。"""

    print("\n处理完成")
    print(f"总计：{result.total} 张")
    print(f"本次新处理：{result.count('success')} 张")
    print(f"已有结果：{result.count('skipped')} 张")
    print(f"失败：{result.count('failed')} 张")
    print(f"耗时：{elapsed:.2f} 秒")
    print(f"输出目录：{output_dir}")


def main(argv: list[str] | None = None) -> int:
    """运行命令行程序，成功返回 0，存在失败任务时返回 1。"""

    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        stream=sys.stdout,
        force=True,
    )

    try:
        # 先基于当前目录建立默认配置，再用命令行参数覆盖指定项。
        config = AppConfig.defaults()
        if args.input_dir:
            config = replace(config, input_dir=_resolve_user_path(args.input_dir))
        if args.output_dir:
            config = replace(config, output_dir=_resolve_user_path(args.output_dir))
        config = replace(
            config,
            scale=args.scale,
            pixel_mode=args.pixel_mode,
            recursive=args.recursive,
        )

        started_at = monotonic()
        if args.file:
            # 单图位于 input 内时归档；外部文件只生成结果，不移动原图。
            source = _resolve_user_path(args.file)
            result = process_one(
                source,
                config,
                force=args.force,
                archive_source=_is_inside(source, config.input_dir),
            )
            batch_result = BatchResult([result])
        else:
            # 重试模式读取 failed，普通批量模式读取 input。
            source_dir = config.failed_dir if args.retry_failed else config.input_dir
            batch_result = process_batch(config, source_dir=source_dir, force=args.force)
    except Exception as error:
        logging.error("[错误] %s", error)
        return 1

    _print_summary(batch_result, monotonic() - started_at, config.output_dir)
    return 1 if batch_result.count("failed") else 0
