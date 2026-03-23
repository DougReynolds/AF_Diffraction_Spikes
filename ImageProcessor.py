import numpy as np
import os
from astropy.visualization import ZScaleInterval, LinearStretch, ImageNormalize
from astropy.io import fits
from astropy.stats import mad_std
from astropy.modeling import models
from astropy.table import Table
from astropy.wcs import WCS
from astropy.stats import SigmaClip
from photutils.background import Background2D, SExtractorBackground, MedianBackground
from photutils.aperture import CircularAperture
from photutils.detection import DAOStarFinder
import matplotlib.pyplot as plt
import cv2
from matplotlib.colors import Normalize
import math
from PIL import Image
from processors.PngProcessor import PngProcessor
from processors.TiffProcessor import TiffProcessor
from processors.JpgProcessor import JpgProcessor
from processors.FitsProcessor import FitsProcessor
from spikes.SpikeRenderer import SpikeRenderer
from SaveImage import SaveImage


class ImageProcessor:
    def __init__(
        self,
        input_image,
        output_image,
        min_threshold,
        max_threshold,
        spike_length_multiplier,
        spike_thickness_multiplier,
        blur_kernel_size,
        blur_multiplier,
        rotation_angle,
    ):
        self.input_image = input_image
        self.output_image = output_image
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold
        self.spike_length_multiplier = spike_length_multiplier
        self.spike_thickness_multiplier = spike_thickness_multiplier
        self.blur_kernel_size = blur_kernel_size
        self.blur_multiplier = blur_multiplier
        self.rotation_angle = rotation_angle
        self.processed_image = None

        self.original_fits_data = None
        self.original_fits_header = None

        self.bit_depth_mode = None

        # FIT save mode: 'scientific' (mono, preserves data) or 'rgb' (3-plane cube)
        self.fit_save_mode = "scientific"

        # QoL: enforce sane defaults (does not override UI, only protects edge cases)
        self.min_threshold = max(1, self.min_threshold)
        self.max_threshold = max(10, self.max_threshold)
        self.spike_length_multiplier = max(0.5, self.spike_length_multiplier)
        self.spike_thickness_multiplier = max(0.2, self.spike_thickness_multiplier)
        self.blur_kernel_size = max(3, int(self.blur_kernel_size))
        self.blur_multiplier = max(0.1, self.blur_multiplier)

    def logInvariants(self, image_type, image_data, detection_data):
        pass

    def process(self):
        import numpy as np
        import cv2

        input_path = self.input_image.strip().lower()

        # Initialize FIT-related state once per run
        self.original_fits_header = None
        self.original_fits_data = None
        try:
            # --- PNG processor ---
            if input_path.endswith(".png"):
                png_processor = PngProcessor(self.input_image)
                data = png_processor.load()
                image_data = data["image_disp"]
                detection_data = data["detection_data"]
                original_color = data["original_color"]
                wcs = data["wcs"]

                self.logInvariants("PNG", image_data, detection_data)
                self.bit_depth_mode = "low"

            elif input_path.endswith((".fit", ".fits")):
                fits_processor = FitsProcessor(self.input_image)
                data = fits_processor.load()

                image_data = data["image_disp"]
                detection_data = data["detection_data"]
                original_color = data["original_color"]
                wcs = data["wcs"]

                self.original_fits_header = data["fits_header"]
                self.original_fits_data = data["fits_data"]

                self.logInvariants("FITS", image_data, detection_data)
                self.bit_depth_mode = "high32"

            else:
                # Non-FITS path (robust TIFF/PNG/JPG handling)
                try:
                    if input_path.endswith((".tif", ".tiff")):
                        tiff_processor = TiffProcessor(self.input_image)
                        data = tiff_processor.load()

                        image_data = data["image_disp"]
                        detection_data = data["detection_data"]
                        original_color = data["original_color"]
                        wcs = data["wcs"]

                        self.logInvariants("TIFF", image_data, detection_data)
                        # Determine TIFF bit depth from detection_data (pre-display conversion)
                        dtype = data.get("original_dtype")

                        if dtype in (np.float32, np.float64, np.uint32):
                            self.bit_depth_mode = "high32"
                        elif dtype == np.uint16:
                            self.bit_depth_mode = "high16"
                        else:
                            self.bit_depth_mode = "low"
                    else:
                        jpg_processor = JpgProcessor(self.input_image)
                        data = jpg_processor.load()

                        image_data = data["image_disp"]
                        detection_data = data["detection_data"]
                        original_color = data["original_color"]
                        wcs = data["wcs"]

                        self.logInvariants("JPG", image_data, detection_data)
                        self.bit_depth_mode = "low"

                except Exception as e:
                    raise RuntimeError(
                        f"Failed to load image '{self.input_image}': {type(e).__name__}: {e}"
                    ) from e

                # No FIT metadata available
                wcs = None

            # Find stars using DAOStarFinder
            # FIT uses original scientific data; PNG/TIFF/JPG use isolated display-space detection_data
            sources = self.detect_stars(detection_data)

            if sources is None or len(sources) == 0:
                # Ensure image is in displayable format (H, W) or (H, W, 3)
                if image_data.ndim == 3:
                    # Convert from (C, H, W) → (H, W, C)
                    image_disp = np.transpose(image_data, (1, 2, 0))
                else:
                    image_disp = image_data

                # Do NOT renormalize final image (preserve visual fidelity)
                image_disp = np.clip(image_disp, 0, 255)
                image_disp = image_disp.astype(np.uint8)

                self.processed_image = image_disp
                return self.processed_image

            # Convert pixel coordinates to world coordinates
            x_centroids = np.array(sources["xcentroid"])
            y_centroids = np.array(sources["ycentroid"])

            # Handle WCS dimensionality safely
            try:
                if wcs is not None and wcs.pixel_n_dim == 2:
                    star_coords = wcs.pixel_to_world(x_centroids, y_centroids)
                elif wcs is not None:
                    # fallback for unexpected dimensionality
                    star_coords = wcs.pixel_to_world(
                        x_centroids, y_centroids, np.zeros_like(x_centroids)
                    )
                else:
                    star_coords = None
            except Exception as e:
                star_coords = None

            if star_coords is not None:
                pass

            # --- Apply diffraction spikes via renderer ---
            if sources is not None and len(sources) > 0:
                # Prepare image for renderer (same as before)
                if "original_color" in locals() and original_color is not None:
                    image_disp = original_color.copy()
                elif image_data.ndim == 3:
                    image_disp = np.transpose(image_data, (1, 2, 0))
                else:
                    image_disp = image_data.copy()

                image_disp = np.clip(image_disp, 0, 255).astype(np.uint8)

                # Build params from GUI-controlled values
                params = {
                    "min_threshold": self.min_threshold,
                    "max_threshold": self.max_threshold,
                    "spike_length_multiplier": self.spike_length_multiplier,
                    "spike_thickness_multiplier": self.spike_thickness_multiplier,
                    "blur_kernel_size": self.blur_kernel_size,
                    "blur_multiplier": self.blur_multiplier,
                    "rotation_angle": self.rotation_angle,
                    "bit_depth_mode": self.bit_depth_mode,
                }

                renderer = SpikeRenderer(params)

                self.processed_image = renderer.render(
                    image=image_disp,
                    sources=sources,
                    input_path=input_path,
                )

                return self.processed_image

            # Fallback (no spikes applied)
            if image_data.ndim == 3:
                image_disp = np.transpose(image_data, (1, 2, 0))
            else:
                image_disp = image_data

            # Do NOT renormalize final image (preserve visual fidelity)
            image_disp = np.clip(image_disp, 0, 255)
            image_disp = image_disp.astype(np.uint8)

            self.processed_image = image_disp
            return self.processed_image
        except Exception as e:
            raise RuntimeError(
                f"Processing failed for '{self.input_image}' (mode={self.bit_depth_mode}): {type(e).__name__}: {e}"
            ) from e

    def display_preview(self, image):
        # Ensure correct shape
        if image.ndim == 3 and image.shape[0] in [3, 4]:
            image = np.transpose(image, (1, 2, 0))

        # Normalize safely for display (no blowout)
        img = image.astype(np.float32)
        img = img - np.percentile(img, 1)
        img = img / (np.percentile(img, 99) + 1e-6)
        img = np.clip(img, 0, 1)

        plt.figure(figsize=(12, 12))
        plt.imshow(img, interpolation="nearest")
        title = os.path.basename(self.output_image) if self.output_image else "Preview"
        plt.title(title)
        ax = plt.gca()
        ax.set_axis_off()
        plt.show()

    def detect_stars(self, image_data):
        if image_data.ndim == 3:
            # FIT cubes may be CHW; display images may be HWC. Handle both safely.
            if image_data.shape[0] in (3, 4) and image_data.shape[-1] not in (3, 4):
                image_data = np.mean(image_data[:3], axis=0)
            elif image_data.shape[-1] in (3, 4):
                image_data = np.mean(image_data[..., :3], axis=2)
            else:
                image_data = np.squeeze(image_data)

        image_data = image_data.astype(np.float32)

        # Proceed as 2D detection
        sigma_clip = SigmaClip(sigma=3.0)

        bkg_estimator = MedianBackground()

        bkg = Background2D(
            image_data,
            (50, 50),
            filter_size=(3, 3),
            sigma_clip=sigma_clip,
            bkg_estimator=bkg_estimator,
        )

        # Subtract background
        image_sub = image_data - bkg.background

        # High-pass filter to suppress nebula (reduced strength to preserve threshold response)
        blur = cv2.GaussianBlur(image_sub, (15, 15), 0)
        image_sub = image_sub - (0.7 * blur)

        # Directly map UI slider to detection threshold (more responsive)
        base_rms = np.median(bkg.background_rms)

        # Restore stronger sensitivity range for UI control
        threshold = base_rms * (self.min_threshold / 3.0)

        # Define an upper flux cap from max_threshold slider (prevents overly bright regions)
        max_flux_limit = None

        daofind = DAOStarFinder(fwhm=5.0, threshold=threshold)
        sources_combined = daofind(image_sub)

        if sources_combined is not None:
            sources_combined = sources_combined[sources_combined["sharpness"] > 0.25]

            if len(sources_combined) > 0:
                # ADD guard before percentile (prevents instability):
                if len(sources_combined) < 10:
                    return sources_combined
                # Direct intuitive mapping
                flux_percentile = max(5, min(95, self.max_threshold * 0.4))
                flux_threshold = np.percentile(
                    sources_combined["flux"], flux_percentile
                )
                sources_combined = sources_combined[
                    sources_combined["flux"] > flux_threshold
                ]

            # NOTE: Peak filtering removed — unreliable in nebula regions

        return sources_combined

    def display_image(self, image_data, sources):
        # Set up the image normalization
        interval = ZScaleInterval()
        vmin, vmax = interval.get_limits(image_data)
        norm = ImageNormalize(vmin=vmin, vmax=vmax, stretch=LinearStretch())

        # Display the image with detected stars
        positions = np.transpose((sources["xcentroid"], sources["ycentroid"]))
        apertures = CircularAperture(positions, r=5)

        # Stack channels to create an RGB image
        rgb_image = np.stack(
            (image_data[0, :, :], image_data[1, :, :], image_data[2, :, :]), axis=-1
        )

        # Normalize pixel values
        normalized_rgb_image = Normalize()(rgb_image)

        plt.figure(figsize=(8, 8))
        plt.imshow(normalized_rgb_image, cmap="viridis", origin="lower", norm=norm)
        apertures.plot(color="red", lw=1.5, alpha=0.5)
        plt.title("FITS Image with Detected Stars")
        plt.show()

    def save(self):
        # Ensure original data is loaded for save pipeline
        if self.original_fits_data is None and self.processed_image is None:
            # Run a lightweight load by calling process() once
            # (process() will populate original_fits_data / detection inputs)
            try:
                self.process()
            except Exception as e:
                raise RuntimeError(
                    f"Save preparation failed for '{self.input_image}': {type(e).__name__}: {e}"
                ) from e

        saver = SaveImage(self)
        saver.save()


if __name__ == "__main__":
    processor = ImageProcessor(
        "your_input.fits", "output_image.png", 10, 1000, 1, 1, 5, 1, 45
    )
    processor.process()
