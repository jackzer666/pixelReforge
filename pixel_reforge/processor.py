"""单张图片的像素化处理。"""

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import cv2
from perfect_pixel import get_perfect_pixel

from .models import ProcessedImage


class ImageProcessingError(RuntimeError):
    """图片无法读取或算法无法生成结果。"""


def process_image(
    source: Path,
    *,
    scale: int,
    pixel_mode: str,
    sample_method: str,
    refine_intensity: float,
) -> ProcessedImage:
    """读取并处理一张图片，返回原始像素图和最近邻放大图。"""

    if not source.is_file():
        raise ImageProcessingError(f"输入图片不存在：{source}")

    bgr = cv2.imread(str(source), cv2.IMREAD_COLOR)
    if bgr is None:
        raise ImageProcessingError(f"无法解析图片，请检查文件是否损坏：{source}")

    if pixel_mode == "source":
        height, width = bgr.shape[:2]
        scaled = cv2.resize(
            bgr,
            (width * scale, height * scale),
            interpolation=cv2.INTER_NEAREST,
        )
        return ProcessedImage(
            width=width,
            height=height,
            original=bgr,
            scaled=scaled,
        )
    if pixel_mode != "detect":
        raise ImageProcessingError(f"不支持的像素模式：{pixel_mode}")

    # OpenCV 读取结果是 BGR，而 perfect-pixel 算法要求 RGB。
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    # 第三方库会直接输出英文调试信息，统一隐藏后由上层输出中文日志。
    with redirect_stdout(StringIO()):
        width, height, output_rgb = get_perfect_pixel(
            rgb,
            sample_method=sample_method,
            refine_intensity=refine_intensity,
            debug=False,
        )

    if width is None or height is None or output_rgb is None:
        raise ImageProcessingError("未检测到有效的像素网格。")

    width = int(width)
    height = int(height)
    # 输出前转回 OpenCV 使用的 BGR，并用最近邻插值保持像素边缘清晰。
    output_bgr = cv2.cvtColor(output_rgb, cv2.COLOR_RGB2BGR)
    scaled = cv2.resize(
        output_bgr,
        (width * scale, height * scale),
        interpolation=cv2.INTER_NEAREST,
    )
    return ProcessedImage(width=width, height=height, original=output_bgr, scaled=scaled)
