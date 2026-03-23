import os
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from astropy.io import fits
import tifffile as tiff

from tkinter import filedialog

from save_files.SaveFIT import SaveFIT
from save_files.SaveTIFF import SaveTIFF
from save_files.SaveJPG import SaveJPG
from save_files.SavePNG import SavePNG
from util.ImageTypeUtil import ImageTypeUtil
from spikes.SpikeRenderer import SpikeRenderer

SPIKE_INTENSITY = 0.5


class SaveImage:
    def __init__(self, processor):
        # Pull everything we need from ImageProcessor
        self.processor = processor

    def display_preview(self, image, output_path=None):
        if image.ndim == 3 and image.shape[0] in [3, 4]:
            image = np.transpose(image, (1, 2, 0))

        img = image.astype(np.float32)
        img = img - np.percentile(img, 1)
        img = img / (np.percentile(img, 99) + 1e-6)
        img = np.clip(img, 0, 1)

        plt.figure(figsize=(12, 12))
        plt.imshow(img, interpolation="nearest")
        title = os.path.basename(output_path) if output_path else "Preview"
        plt.title(title)
        plt.axis("off")
        plt.show()

    def save(self):
        processor = self.processor

        # Always operate from original data
        if processor.original_fits_data is not None:
            original = processor.original_fits_data.astype(np.float32)
        else:
            # fallback for non-FITS input
            if processor.processed_image is None:
                print("No data available to save.")
                return
            original = processor.processed_image.astype(np.float32)

        output_path = (processor.output_image or "").strip()

        if not output_path:
            output_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[
                    ("PNG files", "*.png"),
                    ("TIFF files", "*.tif *.tiff"),
                    ("JPEG files", "*.jpg"),
                    ("FITS files", "*.fit *.fits"),
                    ("All files", "*.*"),
                ],
            )

            if not output_path:
                print("Save cancelled.")
                return

            processor.output_image = output_path

        ext = os.path.splitext(output_path)[1].lower()

        if ext == ".":
            output_path = output_path.rstrip(".") + ".png"
            ext = ".png"

        # Use ImageTypeUtil to determine renderer/type
        img_type = ImageTypeUtil.get_image_type(output_path)

        if img_type == "fit":
            SaveFIT(processor).save(output_path)
            return
        elif img_type == "tiff":
            SaveTIFF(processor).save(output_path)
            return
        elif img_type == "jpg":
            SaveJPG(processor).save(output_path)
            return
        elif img_type == "png":
            SavePNG(processor).save(output_path)
            return

        # --- BMP ---
        if ext == ".bmp":
            data = self._render_from_original(original, mode="standard")
            norm = (data - np.min(data)) / (np.max(data) - np.min(data) + 1e-6)
            img_8 = (norm * 255).astype(np.uint8)

            img = Image.fromarray(img_8)
            img.save(output_path)

            print(f"Saved output to {output_path}")
            return

        # fallback
        img = Image.fromarray(original)
        fallback = output_path + ".png"
        img.save(fallback)
        print(f"Unknown extension. Saved as {fallback}")

    def _render_from_original(self, original, mode="default"):
        processor = self.processor

        min_val = np.min(original)
        max_val = np.max(original)
        norm = (original - min_val) / (max_val - min_val + 1e-6)
        display = (norm * 255).astype(np.uint8)

        if display.ndim == 2:
            display_rgb = np.stack([display] * 3, axis=-1)
        elif display.ndim == 3 and display.shape[0] in (3, 4):
            display_rgb = np.transpose(display[:3], (1, 2, 0))
        else:
            display_rgb = display

        params = {
            "min_threshold": processor.min_threshold,
            "max_threshold": processor.max_threshold,
            "spike_length_multiplier": processor.spike_length_multiplier,
            "spike_thickness_multiplier": processor.spike_thickness_multiplier,
            "blur_kernel_size": processor.blur_kernel_size,
            "blur_multiplier": processor.blur_multiplier,
            "rotation_angle": processor.rotation_angle,
        }

        renderer = SpikeRenderer(params)
        sources = processor.detect_stars(original)

        rendered = renderer.render(
            image=display_rgb,
            sources=sources,
            input_path=processor.input_image.lower(),
        )

        rendered_gray = np.mean(rendered.astype(np.float32), axis=2)
        rendered_norm = rendered_gray / 255.0
        # TEMP: amplify spikes for debugging visibility
        # Mode-specific intensity control
        intensity = SPIKE_INTENSITY

        if mode == "visual":
            intensity = SPIKE_INTENSITY * 1.0
        elif mode == "standard":
            intensity = SPIKE_INTENSITY * 1.0
        elif mode == "tiff":
            intensity = SPIKE_INTENSITY
        elif mode == "scientific":
            intensity = SPIKE_INTENSITY

        result = original + (rendered_norm * np.max(original) * intensity)

        print("DEBUG:")
        print("original min/max:", np.min(original), np.max(original))
        print("rendered_norm min/max:", np.min(rendered_norm), np.max(rendered_norm))
        print("final data min/max:", np.min(result), np.max(result))

        return result
