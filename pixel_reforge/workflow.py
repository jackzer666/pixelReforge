"""单图和批量处理工作流。"""

import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from .config import AppConfig
from .fingerprint import build_task_id, calculate_sha256
from .models import BatchResult, ProcessResult
from .naming import build_output_paths
from .processor import process_image
from .scanner import scan_images
from .state import JsonStateStore


LOGGER = logging.getLogger(__name__)


def _unique_destination(source: Path, directory: Path) -> Path:
    """为归档原图生成不覆盖现有文件的目标路径。"""

    destination = directory / source.name
    if not destination.exists():
        return destination

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    counter = 0
    while True:
        unique_time = timestamp if counter == 0 else f"{timestamp}_{counter}"
        destination = directory / f"{source.stem}_{unique_time}{source.suffix}"
        if not destination.exists():
            return destination
        counter += 1


def _move_source(source: Path, directory: Path) -> Path:
    """将源文件移动到目标目录，并返回最终归档路径。"""

    directory.mkdir(parents=True, exist_ok=True)
    destination = _unique_destination(source, directory)
    return Path(shutil.move(str(source), str(destination)))


def _write_outputs_atomically(
    original_path: Path,
    scaled_path: Path,
    original_image: np.ndarray,
    scaled_image: np.ndarray,
) -> None:
    """先写入两个临时图片，成功后再替换为正式输出。"""

    original_temp = original_path.with_name(f".{original_path.stem}.tmp.png")
    scaled_temp = scaled_path.with_name(f".{scaled_path.stem}.tmp.png")
    temporary_paths = (original_temp, scaled_temp)

    try:
        # 只有两个临时文件都写入成功，才开始发布正式输出。
        if not cv2.imwrite(str(original_temp), original_image):
            raise OSError(f"保存图片失败：{original_path}")
        if not cv2.imwrite(str(scaled_temp), scaled_image):
            raise OSError(f"保存图片失败：{scaled_path}")
        os.replace(original_temp, original_path)
        os.replace(scaled_temp, scaled_path)
    finally:
        for temporary in temporary_paths:
            if temporary.exists():
                try:
                    temporary.unlink()
                except OSError:
                    pass


def _move_to_failed_if_possible(source: Path, failed_dir: Path) -> str | None:
    """尽量将失败原图移入 failed，返回附加错误而不是抛出。"""

    failed_dir = failed_dir.resolve()
    if not source.exists() or source.is_relative_to(failed_dir):
        return None
    try:
        _move_source(source, failed_dir)
    except OSError as error:
        return f"移动到失败目录失败：{error}"
    return None


def _finish_failed_task(
    *,
    source: Path,
    config: AppConfig,
    state: JsonStateStore,
    task_id: str,
    error: Exception,
    archive_source: bool,
) -> ProcessResult:
    """记录失败并尽量隔离原图，附加操作不能掩盖最初错误。"""

    message = str(error) or error.__class__.__name__
    extra_errors: list[str] = []

    try:
        state.mark_failed(task_id, message)
    except Exception as state_error:
        extra_errors.append(f"写入失败记录失败：{state_error}")

    if archive_source:
        move_error = _move_to_failed_if_possible(source, config.failed_dir)
        if move_error:
            extra_errors.append(move_error)

    if extra_errors:
        message = f"{message}；{'；'.join(extra_errors)}"
    LOGGER.error("[失败] %s，%s", source.name, message)
    return ProcessResult(source=source, status="failed", error=message)


def process_one(
    source: Path,
    config: AppConfig,
    *,
    state: JsonStateStore | None = None,
    force: bool = False,
    archive_source: bool = False,
) -> ProcessResult:
    """完成单图去重、处理、状态记录及可选的原图归档。"""

    source = source.expanduser().resolve()
    config.ensure_directories()
    state = state or JsonStateStore(config.state_file)
    parameters = config.processing_parameters()

    # 文件内容指纹与算法参数共同决定任务是否已经完成。
    try:
        source_hash = calculate_sha256(source)
    except OSError as error:
        message = f"无法读取文件：{error}"
        if archive_source:
            move_error = _move_to_failed_if_possible(source, config.failed_dir)
            if move_error:
                message = f"{message}；{move_error}"
        LOGGER.error("[失败] %s，%s", source.name, message)
        return ProcessResult(source=source, status="failed", error=message)

    task_id = build_task_id(source_hash, parameters)
    # 只有状态成功且两个输出文件都存在，才可以复用已有结果。
    if not force and state.has_complete_outputs(task_id):
        record = state.get(task_id) or {}
        outputs = [Path(path) for path in record.get("outputs", [])]
        if archive_source:
            try:
                _move_source(source, config.processed_dir)
            except OSError as error:
                LOGGER.warning(
                    "[警告] %s 已有处理结果，但归档原图失败：%s",
                    source.name,
                    error,
                )
        LOGGER.info("[已有结果] %s，图片和处理参数均未变化", source.name)
        return ProcessResult(source=source, status="skipped", outputs=outputs)

    LOGGER.info("[处理中] %s", source.name)
    # 处理开始前落盘，程序意外中断后该任务不会被误认为成功。
    state.mark_processing(
        task_id,
        source=source,
        source_hash=source_hash,
        parameters=parameters,
    )

    try:
        # 核心算法不直接操作状态和归档，只返回图片数据。
        processed = process_image(
            source,
            scale=config.scale,
            pixel_mode=config.pixel_mode,
            sample_method=config.sample_method,
            refine_intensity=config.refine_intensity,
        )
        original_path, scaled_path = build_output_paths(
            source,
            config.output_dir,
            config.scale,
        )
        _write_outputs_atomically(
            original_path,
            scaled_path,
            processed.original,
            processed.scaled,
        )
        outputs = [original_path, scaled_path]
        state.mark_success(task_id, outputs)
    except Exception as error:
        return _finish_failed_task(
            source=source,
            config=config,
            state=state,
            task_id=task_id,
            error=error,
            archive_source=archive_source,
        )

    # 输出与状态已经成功保存。
    # 归档失败只做警告，下次通过已有记录再次尝试。
    if archive_source:
        try:
            _move_source(source, config.processed_dir)
        except OSError as error:
            LOGGER.warning(
                "[警告] %s 处理成功，但归档原图失败：%s",
                source.name,
                error,
            )

    LOGGER.info(
        "[成功] %s，像素网格：%d × %d",
        source.name,
        processed.width,
        processed.height,
    )
    return ProcessResult(source=source, status="success", outputs=outputs)


def process_batch(
    config: AppConfig,
    *,
    source_dir: Path | None = None,
    force: bool = False,
) -> BatchResult:
    """扫描并逐张处理目录，任意单图失败均不影响后续任务。"""

    config.ensure_directories()
    directory = (source_dir or config.input_dir).resolve()
    managed_directories = (
        config.output_dir.resolve(),
        config.processed_dir.resolve(),
        config.failed_dir.resolve(),
        config.state_file.parent.resolve(),
    )
    # 输入目录可能是项目根目录，递归时必须排除输出和状态目录。
    excluded_directories = tuple(
        candidate
        for candidate in managed_directories
        if candidate != directory and candidate.is_relative_to(directory)
    )
    sources = scan_images(
        directory,
        recursive=config.recursive,
        excluded_directories=excluded_directories,
    )
    state = JsonStateStore(config.state_file)
    result = BatchResult()

    for source in sources:
        try:
            item_result = process_one(
                source,
                config,
                state=state,
                force=force,
                archive_source=True,
            )
        except Exception as error:
            # 单张图片的意外异常不能中断整个批处理任务。
            LOGGER.error("[失败] %s，发生未预期错误：%s", source.name, error)
            item_result = ProcessResult(source=source, status="failed", error=str(error))
        result.add(item_result)
    return result
