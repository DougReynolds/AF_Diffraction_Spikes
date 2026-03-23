from processors.BaseImageProcessorInterface import (
    BaseImageProcessorInterface,
    ProcessorResult,
)

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS


class FitsProcessor(BaseImageProcessorInterface):
    def load(self) -> ProcessorResult:
        hdu = fits.open(self.input_path)[0]

        data = hdu.data.astype(np.float32)

        # Ensure detection_data is 2D (collapse channels if needed)
        if data.ndim == 3:
            detection_data = np.mean(data, axis=0)
        else:
            detection_data = data.copy()

        # Create WCS object
        wcs = WCS(hdu.header)

        # Prepare display image (normalized to 0–255)
        p_low = np.percentile(data, 0.5)
        p_high = np.percentile(data, 99.5)

        if p_high > p_low:
            norm = (data - p_low) / (p_high - p_low)
        else:
            norm = np.zeros_like(data)

        norm = np.clip(norm, 0, 1)

        image_disp = (norm * 255).astype(np.uint8)

        # Ensure display is HWC (OpenCV compatible)
        if image_disp.ndim == 2:
            image_disp = np.stack([image_disp] * 3, axis=-1)
        elif image_disp.ndim == 3:
            # Convert CHW → HWC if needed
            if image_disp.shape[0] in (3, 4):
                image_disp = np.transpose(image_disp[:3], (1, 2, 0))

        original_color = image_disp.copy()

        return {
            "image_disp": image_disp,
            "detection_data": detection_data,
            "original_color": original_color,
            "wcs": wcs,
            "fits_header": hdu.header.copy(),
            "fits_data": data.copy(),
        }
