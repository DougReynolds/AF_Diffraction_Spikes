from processors.BaseImageProcessorInterface import (
    BaseImageProcessorInterface,
    ProcessorResult,
)

import numpy as np
import tifffile as tiff


class TiffProcessor(BaseImageProcessorInterface):
    def load(self) -> ProcessorResult:
        data = tiff.imread(self.input_path)
        original_dtype = data.dtype

        # Convert to float32 for safe processing
        data = data.astype(np.float32)

        # --- Normalize (match current behavior exactly)
        p_low = np.percentile(data, 0.5)
        p_high = np.percentile(data, 99.5)

        if p_high > p_low:
            data = (data - p_low) / (p_high - p_low)
        else:
            data = np.zeros_like(data)

        data = np.clip(data, 0, 1)

        # --- Detection data (float grayscale)
        detection_data = data.copy()
        detection_data = self._to_grayscale(detection_data)

        # --- Display image (uint8 RGB)
        image_disp = (data * 255).astype(np.uint8)

        # --- Original color (for spike rendering)
        original_color = image_disp.copy()

        # If grayscale input, no color
        if image_disp.ndim != 3:
            original_color = None

        return {
            "image_disp": image_disp,
            "detection_data": detection_data,
            "original_color": original_color,
            "original_dtype": original_dtype,
            "wcs": None,
            "fits_header": None,
            "fits_data": None,
        }
