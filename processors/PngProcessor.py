from PIL import Image
import numpy as np

from processors.BaseImageProcessorInterface import (
    BaseImageProcessorInterface,
    ProcessorResult,
)


class PngProcessor(BaseImageProcessorInterface):
    def load(self) -> ProcessorResult:
        img = Image.open(self.input_path)

        # Ensure RGB
        if img.mode == "RGBA":
            img = img.convert("RGB")

        image_data = np.array(img)

        # --- Display image (uint8 RGB)
        image_disp = image_data.copy()

        # --- Detection data (float grayscale)
        detection_data = image_data.astype(np.float32) / 255.0
        detection_data = self._to_grayscale(detection_data)

        # --- Original color (used for rendering spikes)
        original_color = image_disp.copy()

        return {
            "image_disp": image_disp,
            "detection_data": detection_data,
            "original_color": original_color,
            "wcs": None,
            "fits_header": None,
            "fits_data": None,
        }
