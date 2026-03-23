import numpy as np
from PIL import Image
import cv2

SPIKE_INTENSITY = 0.5


class SaveJPG:
    def __init__(self, processor):
        self.processor = processor

    def save(self, output_path):
        p = self.processor

        # Load original JPG/PNG data from disk (not preview)
        try:
            original = cv2.imread(p.input_image, cv2.IMREAD_UNCHANGED)
            if original is None:
                raise ValueError("Failed to load image")

            # Convert BGR → RGB if needed
            if len(original.shape) == 3:
                original = cv2.cvtColor(original, cv2.COLOR_BGR2RGB)

            original = original.astype(np.float32)

        except Exception as e:
            print(f"Failed to load original image data: {e}")
            return

        data = self._render(original)

        # Normalize to 8-bit
        norm = (data - np.min(data)) / (np.max(data) - np.min(data) + 1e-6)
        img_8 = (norm * 255).astype(np.uint8)

        img = Image.fromarray(img_8)
        img.save(output_path, quality=100, subsampling=0)

        print(f"Saved JPG to {output_path}")

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
            spike = np.expand_dims(spike, axis=2)

        return original + spike
