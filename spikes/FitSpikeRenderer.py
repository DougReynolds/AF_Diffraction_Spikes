from spikes.BaseSpikeRendererLogic import BaseSpikeRendererLogic


class FitSpikeRenderer(BaseSpikeRendererLogic):
    def __init__(self, params):
        self.params = params
        self._bit_depth_mode = "high32"

    def set_bit_depth_mode(self, mode: str):
        self._bit_depth_mode = mode

    def get_bit_depth_mode(self) -> str:
        return self._bit_depth_mode

    def render(self, image, sources, input_path=None):
        """
        FITS-specific rendering wrapper.
        Uses scientific tuning parameters.
        """

        return self._render_common(
            image=image,
            sources=sources,
            input_path=input_path,
            is_fits=True,
            threshold=self.get_threshold(),
            flux_boost=self.get_flux_boost(),
            bit_depth_mode=self.get_bit_depth_mode(),
        )

    def get_threshold(self):
        return self.params.get("min_threshold", 25.0) / 255.0

    def get_flux_boost(self):
        return self.params.get("flux_boost", 1.0)
