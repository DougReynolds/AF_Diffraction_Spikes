from abc import ABC, abstractmethod
from typing import TypedDict, Optional, Any
import numpy as np


class ProcessorResult(TypedDict):
    image_disp: np.ndarray
    detection_data: np.ndarray
    original_color: Optional[np.ndarray]
    wcs: Optional[Any]
    fits_header: Optional[Any]
    fits_data: Optional[np.ndarray]


class BaseImageProcessorInterface(ABC):
    """
    Base interface for all image processors.

    Each processor must:
    - Load the image
    - Normalize/prepare data
    - Return a standardized dict used by ImageProcessor
    """

    def __init__(self, input_path: str):
        self.input_path = input_path

    @abstractmethod
    def load(self) -> ProcessorResult:
        """
        Load and process the image.

        Returns:
            dict with keys:
                - image_disp (uint8 RGB)
                - detection_data (float32 grayscale)
                - original_color (RGB or None)
                - wcs (optional)
                - fits_header (optional)
                - fits_data (optional)
        """
        raise NotImplementedError(
            "Processors must implement load() and return ProcessorResult"
        )

    def _to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """
        Utility: convert RGB → grayscale for detection.
        """

        if image.ndim == 3:
            return np.mean(image, axis=2)
        return image

    def _normalize_01(self, data: np.ndarray) -> np.ndarray:
        """
        Utility: normalize array to 0–1 range using percentiles.
        """

        p_low = np.percentile(data, 0.5)
        p_high = np.percentile(data, 99.5)

        if p_high > p_low:
            data = (data - p_low) / (p_high - p_low)
        else:
            data = np.zeros_like(data)

        return np.clip(data, 0, 1)
