import numpy as np
import tifffile as tiff

SPIKE_INTENSITY = 0.5


class SaveTIFF:
    def __init__(self, processor):
        self.processor = processor

    def save(self, output_path):
        p = self.processor

        # TIFF save should work from the original TIFF source data
        try:
            original = tiff.imread(p.input_image).astype(np.float32)
        except Exception as e:
            print(f"Failed to load original TIFF data: {e}")
            return

        data = self._render(original)

        # Normalize to 16-bit
        norm = (data - np.min(data)) / (np.max(data) - np.min(data) + 1e-6)
        img_16 = (norm * 65535).astype(np.uint16)

        tiff.imwrite(output_path, img_16)
        print(f"Saved TIFF to {output_path}")

    def _render(self, original):
        p = self.processor

        # Normalize for rendering
        min_val = np.min(original)
        max_val = np.max(original)
        norm = (original - min_val) / (max_val - min_val + 1e-6)
        display = (norm * 255).astype(np.uint8)

        # Ensure RGB for renderer
        if display.ndim == 2:
            display_rgb = np.stack([display] * 3, axis=-1)
        elif display.ndim == 3 and display.shape[0] in (3, 4):
            display_rgb = np.transpose(display[:3], (1, 2, 0))
        else:
            display_rgb = display

        from spikes.SpikeRenderer import SpikeRenderer

        params = {
            "min_threshold": p.min_threshold,
            "max_threshold": p.max_threshold,
            "spike_length_multiplier": p.spike_length_multiplier,
            "spike_thickness_multiplier": p.spike_thickness_multiplier,
            "blur_kernel_size": p.blur_kernel_size,
            "blur_multiplier": p.blur_multiplier,
            "rotation_angle": p.rotation_angle,
        }

        renderer = SpikeRenderer(params)
        sources = p.detect_stars(original)

        rendered = renderer.render(
            image=display_rgb,
            sources=sources,
            input_path=p.input_image.lower(),
        )

        rendered_gray = np.mean(rendered.astype(np.float32), axis=2)
        rendered_norm = rendered_gray / 255.0

        spike = rendered_norm * np.max(original) * SPIKE_INTENSITY

        # Match dimensions
        if original.ndim == 3:
            if original.shape[0] in (3, 4):
                spike = np.expand_dims(spike, axis=0)
            else:
                spike = np.expand_dims(spike, axis=2)

        return original + spike
