from spikes.BaseSpikeRendererLogic import BaseSpikeRendererLogic

# TIFF-specific tuning constants

TIFF_THRESHOLD = 0.15
TIFF_FLUX_BOOST = 1.0


class TiffSpikeRenderer(BaseSpikeRendererLogic):
    def __init__(self, params):
        self.params = params
        self._bit_depth_mode = "low"

    def set_bit_depth_mode(self, mode: str):
        self._bit_depth_mode = mode

    def get_bit_depth_mode(self) -> str:
        return self._bit_depth_mode

    def render(self, image, sources, input_path=None):
        """
        TIFF-specific rendering wrapper.
        Uses high-bit-depth friendly tuning parameters.
        """
        # Use bit depth mode from params (source of truth)
        mode = self.params.get("bit_depth_mode")
        if mode:
            self.set_bit_depth_mode(mode)

        return self._render_common(
            image=image,
            sources=sources,
            input_path=input_path,
            is_fits=False,
            threshold=self.get_threshold(),
            flux_boost=self.get_flux_boost(),
            bit_depth_mode=self.get_bit_depth_mode(),
        )

    def get_threshold(self):
        return self.params.get("min_threshold", 25.0) / 255.0

    def get_flux_boost(self):
        return self.params.get("flux_boost", 1.0)
