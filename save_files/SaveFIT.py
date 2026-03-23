from astropy.io import fits
import numpy as np

SPIKE_INTENSITY = 0.5


class SaveFIT:
    def __init__(self, processor):
        self.processor = processor

    def save(self, output_path):
        p = self.processor

        if p.original_fits_data is None:
            print("No original data available for FITS save.")
            return

        original = p.original_fits_data.astype(np.float32)

        # Render with mode awareness
        mode = getattr(p, "fit_save_mode", "scientific")
        data = self._render(original, mode)

        # Ensure correct channel ordering (C, H, W)
        if data.ndim == 3:
            if data.shape[0] not in (3, 4):
                data = np.transpose(data, (2, 0, 1))

        hdu = fits.PrimaryHDU(data.astype(np.float32))

        # Preserve original header if available
        if p.original_fits_header is not None:
            for key, value in p.original_fits_header.items():
                try:
                    if key not in ("SIMPLE", "BITPIX", "NAXIS", "EXTEND"):
                        hdu.header[key] = value
                except Exception:
                    pass

        hdu.writeto(output_path, overwrite=True)
        print(f"Saved FITS to {output_path} (mode={mode})")

    def _render(self, original, mode):
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

        params = {
            "min_threshold": p.min_threshold,
            "max_threshold": p.max_threshold,
            "spike_length_multiplier": p.spike_length_multiplier,
            "spike_thickness_multiplier": p.spike_thickness_multiplier,
            "blur_kernel_size": p.blur_kernel_size,
            "blur_multiplier": p.blur_multiplier,
            "rotation_angle": p.rotation_angle,
        }

        from spikes.SpikeRenderer import SpikeRenderer

        renderer = SpikeRenderer(params)
        sources = p.detect_stars(original)

        rendered = renderer.render(
            image=display_rgb,
            sources=sources,
            input_path=p.input_image.lower(),
        )

        rendered_gray = np.mean(rendered.astype(np.float32), axis=2)
        rendered_norm = rendered_gray / 255.0

        # Mode-specific intensity
        intensity = SPIKE_INTENSITY

        spike = rendered_norm * np.max(original) * intensity

        # Match dimensions for broadcasting
        if original.ndim == 3:
            if original.shape[0] in (3, 4):
                spike = np.expand_dims(spike, axis=0)
            else:
                spike = np.expand_dims(spike, axis=2)

        return original + spike
