"""单图像素处理模式测试。"""

import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from pixel_reforge.processor import process_image


class ProcessorTests(unittest.TestCase):
    """验证自动检测以外的原图像素直通模式。"""

    def test_source_mode_treats_each_input_pixel_as_one_logical_pixel(self) -> None:
        """source 模式的 1x 尺寸应等于输入，预览图应严格按倍数放大。"""

        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source.png"
            image = np.array(
                [
                    [[0, 0, 0], [10, 20, 30], [40, 50, 60]],
                    [[70, 80, 90], [100, 110, 120], [130, 140, 150]],
                ],
                dtype=np.uint8,
            )
            self.assertTrue(cv2.imwrite(str(source), image))

            result = process_image(
                source,
                scale=3,
                pixel_mode="source",
                sample_method="center",
                refine_intensity=0.3,
            )

            self.assertEqual((result.width, result.height), (3, 2))
            np.testing.assert_array_equal(result.original, image)
            self.assertEqual(result.scaled.shape[:2], (6, 9))
            np.testing.assert_array_equal(
                result.scaled,
                np.repeat(np.repeat(image, 3, axis=0), 3, axis=1),
            )


if __name__ == "__main__":
    unittest.main()
