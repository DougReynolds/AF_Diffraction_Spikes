from abc import ABC, abstractmethod
from typing import Any, Optional


import numpy as np
import cv2

# --- Individual renderer imports ---
from spikes.PngSpikeRenderer import PngSpikeRenderer
from spikes.JpgSpikeRenderer import JpgSpikeRenderer
from spikes.TiffSpikeRenderer import TiffSpikeRenderer
from spikes.FitSpikeRenderer import FitSpikeRenderer
from spikes.BaseSpikeRendererLogic import BaseSpikeRendererLogic
from util.ImageTypeUtil import ImageTypeUtil


class SpikeRendererInterface(ABC):
    """
    Contract for spike rendering implementations.
    """

    @abstractmethod
    def render(
        self,
        image: np.ndarray,
        sources: Any,
        input_path: str,
    ) -> np.ndarray:
        """
        Args:
            image: HWC uint8 image
            sources: detected star sources
            input_path: source file path

        Returns:
            np.ndarray: HWC uint8 image with spikes applied
        """
        raise NotImplementedError


class SpikeRenderer(SpikeRendererInterface):
    """
    Responsible for rendering diffraction spikes on detected stars.

    This class is intentionally isolated from:
    - Image loading
    - Detection
    - Saving
    """

    def __init__(self, params: dict):
        self.params = params
        self.png_renderer = PngSpikeRenderer(params)
        self.jpg_renderer = JpgSpikeRenderer(params)
        self.tiff_renderer = TiffSpikeRenderer(params)
        self.fit_renderer = FitSpikeRenderer(params)

    def render(
        self,
        image: np.ndarray,
        sources: Any,
        input_path: str,
    ) -> np.ndarray:
        # Work on a copy (no side effects)
        image_disp = np.ascontiguousarray(image.copy())

        # Ensure 3-channel image
        if image_disp.ndim == 3 and image_disp.shape[2] == 4:
            image_disp = image_disp[:, :, :3]
        elif image_disp.ndim == 2:
            image_disp = cv2.cvtColor(image_disp, cv2.COLOR_GRAY2RGB)

        image_disp = np.ascontiguousarray(image_disp)

        # Use bit depth mode from params (source of truth)
        bit_depth_mode = self.params.get("bit_depth_mode", "low")

        # Propagate to all renderers
        self.png_renderer.set_bit_depth_mode(bit_depth_mode)
        self.jpg_renderer.set_bit_depth_mode(bit_depth_mode)
        self.tiff_renderer.set_bit_depth_mode(bit_depth_mode)
        self.fit_renderer.set_bit_depth_mode(bit_depth_mode)

        renderer_for_type = ImageTypeUtil.get_renderer_for_path(input_path, self)
        return renderer_for_type.render(image_disp, sources, input_path)
