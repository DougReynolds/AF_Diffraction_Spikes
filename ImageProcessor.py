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

        # FIT save mode: 'scientific' (mono, preserves data) or 'rgb' (3-plane cube)
        self.fit_save_mode = "scientific"

        # QoL: enforce sane defaults (does not override UI, only protects edge cases)
        self.min_threshold = max(1, self.min_threshold)
        self.max_threshold = max(10, self.max_threshold)
        self.spike_length_multiplier = max(0.5, self.spike_length_multiplier)
        self.spike_thickness_multiplier = max(0.2, self.spike_thickness_multiplier)
        self.blur_kernel_size = max(3, int(self.blur_kernel_size))
        self.blur_multiplier = max(0.1, self.blur_multiplier)

    def process(self):
        import numpy as np
        import cv2

        # --- Format-aware load ---
        if self.input_image.lower().endswith((".fit", ".fits")):
            hdu_list = fits.open(self.input_image)
            image_data = hdu_list[0].data

            # Store original FITS header for metadata preservation
            self.original_fits_header = hdu_list[0].header.copy()

            # Preserve original scientific data for FIT export
            self.original_fits_data = image_data.copy()

            # FIT path uses original scientific data for detection (keep isolated from PNG/TIFF workflow)
            detection_data = image_data.copy()

            # Create a WCS object to handle celestial coordinates
            wcs = WCS(hdu_list[0].header)

        else:
            # Non-FITS path (robust TIFF/PNG/JPG handling)
            try:
                if self.input_image.lower().endswith((".tif", ".tiff")):
                    import tifffile as tiff

                    data = tiff.imread(self.input_image)

                    # Convert to float for safe processing
                    data = data.astype(np.float32)

                    # Percentile-based clipping (preserves star contrast like JPG)
                    p_low = np.percentile(data, 0.5)
                    p_high = np.percentile(data, 99.5)

                    if p_high > p_low:
                        data = (data - p_low) / (p_high - p_low)
                    else:
                        data = np.zeros_like(data)

                    data = np.clip(data, 0, 1)

                    # Use float data for detection (preserves dynamic range)
                    detection_data = data.copy()

                    # Prepare display image (uint8)
                    image_data = (data * 255).astype(np.uint8)

                    # Preserve original color data
                    original_color = image_data.copy()

                    # Create grayscale for detection
                    if detection_data.ndim == 3:
                        detection_data = np.mean(detection_data, axis=2)
                    else:
                        original_color = None
                else:
                    img = Image.open(self.input_image)

                    # Convert RGBA → RGB if needed
                    if img.mode == "RGBA":
                        img = img.convert("RGB")

                    image_data = np.array(img)

                    # Preserve original color data
                    original_color = image_data.copy() if image_data.ndim == 3 else None

                    # Create float detection data (0–1 range)
                    detection_data = image_data.astype(np.float32) / 255.0

                    # Convert to grayscale for detection
                    if detection_data.ndim == 3:
                        detection_data = np.mean(detection_data, axis=2)

            except Exception as e:
                raise RuntimeError(f"Failed to load image for processing: {e}")

            # No FIT metadata available
            self.original_fits_header = None
            self.original_fits_data = None
            wcs = None

        # Find stars using DAOStarFinder
        # FIT uses original scientific data; PNG/TIFF/JPG use isolated display-space detection_data
        sources = self.detect_stars(detection_data)

        if sources is None or len(sources) == 0:
            print("No sources detected - skipping processing")
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

        print(f"Detected {len(sources) if sources is not None else 0} sources")

        # Convert pixel coordinates to world coordinates
        x_centroids = np.array(sources["xcentroid"])
        y_centroids = np.array(sources["ycentroid"])

        # Handle WCS dimensionality safely
        try:
            if wcs.pixel_n_dim == 2:
                star_coords = wcs.pixel_to_world(x_centroids, y_centroids)
            else:
                # fallback for unexpected dimensionality
                star_coords = wcs.pixel_to_world(
                    x_centroids, y_centroids, np.zeros_like(x_centroids)
                )
        except Exception as e:
            print(f"WCS conversion skipped: {e}")
            star_coords = None

        if star_coords is not None:
            print("Detected Star Coordinates (RA, Dec):")
            print(star_coords[:10], " ...")  # preview only

        # --- Apply diffraction spikes ---
        if sources is not None and len(sources) > 0:
            # Prepare image for drawing
            if "original_color" in locals() and original_color is not None:
                image_disp = original_color.copy()
            elif image_data.ndim == 3:
                image_disp = np.transpose(image_data, (1, 2, 0))
            else:
                image_disp = image_data.copy()

            # Normalize to 0–255 uint8
            image_disp = image_disp - np.min(image_disp)
            if np.max(image_disp) > 0:
                image_disp = image_disp / np.max(image_disp)

            image_disp = (image_disp * 255).astype(np.uint8, copy=True)

            # Ensure OpenCV-compatible memory layout
            image_disp = np.ascontiguousarray(image_disp)

            # Ensure 3-channel image (strip alpha if present)
            if image_disp.ndim == 3 and image_disp.shape[2] == 4:
                image_disp = image_disp[:, :, :3]
            elif len(image_disp.shape) == 2:
                image_disp = cv2.cvtColor(image_disp, cv2.COLOR_GRAY2RGB)

            # Ensure contiguous after color conversion
            image_disp = np.ascontiguousarray(image_disp)

            h, w = image_disp.shape[:2]

            # Supersampled overlay for smoother spikes (2x resolution)
            scale_ss = 2
            overlay_ss = cv2.resize(
                image_disp, (w * scale_ss, h * scale_ss), interpolation=cv2.INTER_LINEAR
            )
            if overlay_ss.ndim == 3 and overlay_ss.shape[2] == 4:
                overlay_ss = overlay_ss[:, :, :3]

            # Precompute for scaling
            max_flux = np.max(sources["flux"]) if len(sources) > 0 else 1.0

            for s in sources[:1000]:  # cap for performance, still visually dense
                x = int(s["xcentroid"] * scale_ss)
                y = int(s["ycentroid"] * scale_ss)

                # Bounds check
                if x < 0 or x >= w * scale_ss or y < 0 or y >= h * scale_ss:
                    continue

                # Use robust normalization to prevent over-saturation (handles TIFF/PNG differences)
                flux_ref = (
                    np.percentile(sources["flux"], 99)
                    if len(sources) > 10
                    else max_flux
                )
                flux_norm = float(s["flux"]) / float(flux_ref) if flux_ref > 0 else 0.0
                flux_norm = min(flux_norm, 1.0)

                # Skip very faint stars (prevents tiny stars getting spikes)
                if flux_norm < 0.15:
                    continue

                # Format-specific spike scaling
                if self.original_fits_data is not None:
                    # Expand usable headroom for length control
                    length = int(
                        (5 + 30 * flux_norm)
                        # Remapped so slider=1.0 ≈ previous ~1.84 behavior
                        * (1.26 + 2.0 * self.spike_length_multiplier)
                    )
                else:
                    # PNG + TIFF share same behavior, JPG unchanged
                    if self.input_image.lower().endswith((".png", ".tif", ".tiff")):
                        # PNG + TIFF share same behavior
                        length = int(
                            (4 + 18 * flux_norm)
                            * (0.46 + 0.6 * self.spike_length_multiplier)
                        )
                    else:
                        # JPG unchanged
                        length = int(
                            (4 + 22 * flux_norm)
                            * (1.26 + 2.0 * self.spike_length_multiplier)
                        )
                if length < 3:
                    continue
                # Reduce non-FIT thickness slightly to avoid chunky crosses
                if self.original_fits_data is not None:
                    thickness = max(
                        1,
                        int(
                            (1 + 3 * flux_norm)
                            # Remapped so slider=1.0 ≈ previous ~1.84 behavior
                            * (1.26 + 2.0 * self.spike_thickness_multiplier)
                        ),
                    )
                else:
                    # PNG + TIFF share same behavior, JPG unchanged
                    if self.input_image.lower().endswith((".png", ".tif", ".tiff")):
                        # PNG + TIFF share same behavior
                        thickness = max(
                            1,
                            int(
                                (1 + 2 * flux_norm)
                                * (0.56 + 1.0 * self.spike_thickness_multiplier)
                            ),
                        )
                    else:
                        thickness = max(
                            1,
                            int(
                                (1 + 2 * flux_norm)
                                * (1.26 + 2.0 * self.spike_thickness_multiplier)
                            ),
                        )

                color = (255, 255, 255)  # white spikes

                # Rotated 4-spike pattern using rotation_angle
                angle_rad = math.radians(self.rotation_angle)
                cos_a = math.cos(angle_rad)
                sin_a = math.sin(angle_rad)

                # Subpixel precision (fixed — removed double scaling bug)
                scale = 256  # subpixel scaling factor (2^8)

                x_fp = int(x * scale)
                y_fp = int(y * scale)

                dx = length * cos_a
                dy = length * sin_a

                x1 = int((x + dx) * scale)
                y1 = int((y + dy) * scale)
                x2 = int((x - dx) * scale)
                y2 = int((y - dy) * scale)

                # perpendicular axis
                dx_p = -length * sin_a
                dy_p = length * cos_a

                x3 = int((x + dx_p) * scale)
                y3 = int((y + dy_p) * scale)
                x4 = int((x - dx_p) * scale)
                y4 = int((y - dy_p) * scale)

                # --- Optical diffraction spike rendering (Gaussian profile) ---
                # Process only a local ROI around each star for performance.
                roi_radius = max(8, int(length * scale_ss * 1.5))
                x0 = max(0, x - roi_radius)
                x1_roi = min(w * scale_ss, x + roi_radius + 1)
                y0 = max(0, y - roi_radius)
                y1_roi = min(h * scale_ss, y + roi_radius + 1)

                roi_h = y1_roi - y0
                roi_w = x1_roi - x0
                if roi_h <= 1 or roi_w <= 1:
                    continue

                # Local coordinates relative to ROI
                x_local = x - x0
                y_local = y - y0

                # Create temporary mask for this star ROI (single channel for precision)
                spike_mask = np.zeros((roi_h, roi_w), dtype=np.float32)

                # Subpixel precision endpoints relative to ROI
                x_fp_local = int(x_local * scale)
                y_fp_local = int(y_local * scale)

                x1_local = int(((x + dx) - x0) * scale)
                y1_local = int(((y + dy) - y0) * scale)
                x2_local = int(((x - dx) - x0) * scale)
                y2_local = int(((y - dy) - y0) * scale)
                x3_local = int(((x + dx_p) - x0) * scale)
                y3_local = int(((y + dy_p) - y0) * scale)
                x4_local = int(((x - dx_p) - x0) * scale)
                y4_local = int(((y - dy_p) - y0) * scale)

                # Draw thin core lines into ROI mask (single channel)
                cv2.line(
                    spike_mask,
                    (x_fp_local, y_fp_local),
                    (x1_local, y1_local),
                    1.0,
                    max(1, thickness),
                    lineType=cv2.LINE_AA,
                    shift=8,
                )
                cv2.line(
                    spike_mask,
                    (x_fp_local, y_fp_local),
                    (x2_local, y2_local),
                    1.0,
                    max(1, thickness),
                    lineType=cv2.LINE_AA,
                    shift=8,
                )
                cv2.line(
                    spike_mask,
                    (x_fp_local, y_fp_local),
                    (x3_local, y3_local),
                    1.0,
                    max(1, thickness),
                    lineType=cv2.LINE_AA,
                    shift=8,
                )
                cv2.line(
                    spike_mask,
                    (x_fp_local, y_fp_local),
                    (x4_local, y4_local),
                    1.0,
                    max(1, thickness),
                    lineType=cv2.LINE_AA,
                    shift=8,
                )

                # --- TRUE diffraction profile ---
                # Strong lateral falloff (perpendicular to spike)
                # Make kernel scale more aggressively with slider
                k_star = max(3, int(self.blur_kernel_size * 2))
                if k_star % 2 == 0:
                    k_star += 1

                sigma_star = max(0.8, self.blur_multiplier * 1.2)
                spike_mask = cv2.GaussianBlur(spike_mask, (k_star, k_star), sigma_star)

                # --- Add longitudinal falloff (critical missing piece) ---
                yy_roi, xx_roi = np.indices((roi_h, roi_w))
                cx = x_local
                cy = y_local

                dx_roi = xx_roi - cx
                dy_roi = yy_roi - cy
                r = np.sqrt(dx_roi * dx_roi + dy_roi * dy_roi)

                # length is in original pixels -> scale to supersampled space
                r_norm = r / (length * scale_ss + 1e-6)

                # Exponential decay from center (optical behavior)
                falloff = np.exp(-2.0 * r_norm)
                spike_mask *= falloff

                if self.original_fits_data is not None:
                    # Reduce FIT spike saturation to restore slider headroom
                    intensity = 150 * (0.6 + 0.8 * flux_norm)
                else:
                    # PNG + TIFF reduced saturation, JPG unchanged
                    if self.input_image.lower().endswith((".png", ".tif", ".tiff")):
                        # PNG + TIFF reduced saturation
                        intensity = 90 * (0.5 + 0.5 * flux_norm)
                    else:
                        # JPG unchanged
                        intensity = 135 * (0.55 + 0.7 * flux_norm)

                # Expand mask to 3 channels and accumulate only into ROI
                spike_rgb = np.repeat(spike_mask[:, :, np.newaxis], 3, axis=2)
                roi = overlay_ss[y0:y1_roi, x0:x1_roi].astype(np.float32)
                roi = np.clip(roi + (spike_rgb * intensity), 0, 255)
                overlay_ss[y0:y1_roi, x0:x1_roi] = roi.astype(np.uint8)

                # Small star core (keeps center realistic)
                cv2.circle(
                    overlay_ss,
                    (x, y),
                    int(1 + 2 * flux_norm),
                    (255, 255, 255),
                    -1,
                    lineType=cv2.LINE_AA,
                )

            # Apply controlled optical blur (respect user blur settings)
            # Match stronger kernel response to slider
            k_opt = max(3, int(self.blur_kernel_size * 2))
            if k_opt % 2 == 0:
                k_opt += 1

            sigma_opt = max(0.3, self.blur_multiplier)
            overlay_ss = cv2.GaussianBlur(overlay_ss, (k_opt, k_opt), sigma_opt)

            # Downsample back to original resolution for smooth anti-aliasing
            overlay = cv2.resize(overlay_ss, (w, h), interpolation=cv2.INTER_AREA)

            # Optional blur for realism (ensure odd kernel)
            k = int(self.blur_kernel_size)
            if k % 2 == 0:
                k += 1
            if k > 1 and self.blur_multiplier > 0:
                # Apply lighter blur to avoid affecting perceived detection/contrast
                overlay = cv2.GaussianBlur(overlay, (k, k), self.blur_multiplier * 0.5)

            # Create mask of only spike pixels (where overlay differs from original)
            mask = np.any(overlay != image_disp, axis=2)

            # Blend ONLY where spikes exist (prevents nebula blowout)
            alpha = 0.85  # slightly stronger core, helps optical look

            for c in range(3):
                image_disp[..., c] = np.where(
                    mask,
                    (overlay[..., c] * alpha + image_disp[..., c] * (1 - alpha)).astype(
                        np.uint8
                    ),
                    image_disp[..., c],
                )

            self.processed_image = image_disp
            # self.display_preview(self.processed_image)
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
        plt.title("Large Preview (Debug)")
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
        if self.processed_image is None:
            print("No processed image to save.")
            return

        try:
            image_to_save = self.processed_image

            # If PIL Image, convert to numpy array
            if isinstance(image_to_save, Image.Image):
                image_to_save = np.array(image_to_save)

            # Clean filename
            self.output_image = (self.output_image or "").strip()

            ext = os.path.splitext(self.output_image)[1].lower()

            # If still empty, assign default filename based on input format
            if self.output_image == "":
                input_ext = os.path.splitext(self.input_image)[1].lower()

                if input_ext in [".fit", ".fits"]:
                    self.output_image = "output.fits"
                elif input_ext in [".tif", ".tiff"]:
                    self.output_image = "output.tiff"
                elif input_ext in [".jpg", ".jpeg"]:
                    self.output_image = "output.jpg"
                elif input_ext in [".png"]:
                    self.output_image = "output.png"
                else:
                    self.output_image = "output.png"
                ext = os.path.splitext(self.output_image)[1].lower()

            # Handle cases like "filename." or invalid extension
            if ext == ".":
                self.output_image = self.output_image.rstrip(".") + ".png"
                ext = ".png"

            # --- FITS save ---
            if ext.endswith((".fit", ".fits")):
                # Mode 1: scientific (preserve original mono data + inject signal)
                if (
                    self.fit_save_mode == "scientific"
                    and self.original_fits_data is not None
                ):
                    data = self.original_fits_data.copy()

                    if self.processed_image is not None:
                        proc = image_to_save.astype(np.float32) / 255.0

                        # collapse RGB to mono mask
                        if proc.ndim == 3:
                            proc = np.mean(proc, axis=2)

                        # ensure proc is 2D
                        if proc.ndim == 3:
                            proc = proc[0]

                        # resize to match spatial dims
                        if proc.shape != data.shape[-2:]:
                            proc = cv2.resize(proc, (data.shape[-1], data.shape[-2]))

                        # handle FIT data shape (2D or 3D cube)
                        if data.ndim == 2:
                            data = data + (proc * np.std(data) * 0.1)
                        elif data.ndim == 3:
                            # apply same mask to all channels
                            for i in range(data.shape[0]):
                                data[i] = data[i] + (proc * np.std(data[i]) * 0.1)

                # Mode 2: RGB display FIT (3-plane cube)
                else:
                    data = image_to_save.astype(np.float32)

                    # ensure 3 channels
                    if data.ndim == 2:
                        data = np.stack([data, data, data], axis=0)
                    elif data.ndim == 3:
                        # HWC -> CHW
                        data = np.transpose(data, (2, 0, 1))

                hdu = fits.PrimaryHDU(data.astype(np.float32))

                # Merge original header safely (preserve metadata, avoid structural conflicts)
                if self.original_fits_header is not None:
                    clean_header = fits.Header()

                    for card in self.original_fits_header.cards:
                        if card.keyword in [
                            "SIMPLE",
                            "BITPIX",
                            "NAXIS",
                            "NAXIS1",
                            "NAXIS2",
                            "NAXIS3",
                            "EXTEND",
                        ]:
                            continue
                        try:
                            clean_header.append(card, end=True)
                        except Exception:
                            pass

                    # extend preserves ordering and comments better than assignment
                    hdu.header.extend(clean_header, update=True, strip=False)
                hdu.writeto(self.output_image, overwrite=True)
                print(f"Saved FITS to {self.output_image} (mode={self.fit_save_mode})")
                return

            # --- TIFF save (use PIL for reliability) ---
            if ext.endswith((".tif", ".tiff")):
                # Convert to 16-bit for high-quality TIFF output
                img_16 = (image_to_save.astype(np.float32) / 255.0 * 65535).astype(
                    np.uint16
                )
                img = Image.fromarray(img_16)
                img.save(self.output_image, compression=None)
                print(f"Saved TIFF to {self.output_image}")
                return

            # --- Standard formats (PNG/JPG via PIL for reliability) ---
            if ext in [".png", ".jpg", ".jpeg", ".bmp"]:

                if ext == ".png":
                    # Convert to 16-bit PNG for higher fidelity
                    img_16 = (image_to_save.astype(np.float32) / 255.0 * 65535).astype(
                        np.uint16
                    )
                    img = Image.fromarray(img_16)
                    img.save(self.output_image, compress_level=0)

                elif ext in [".jpg", ".jpeg"]:
                    img = Image.fromarray(image_to_save)
                    # Max quality JPEG (8-bit by spec)
                    img.save(self.output_image, quality=100, subsampling=0)

                else:
                    img = Image.fromarray(image_to_save)
                    img.save(self.output_image)

                print(f"Saved output to {self.output_image}")
                return

            # Fallback (unknown extension)
            img = Image.fromarray(image_to_save)
            fallback_path = self.output_image + ".png"
            img.save(fallback_path)
            print(f"Unknown extension. Saved as {fallback_path}")

        except Exception as e:
            print(f"Error saving image: {e}")


if __name__ == "__main__":
    processor = ImageProcessor(
        "your_input.fits", "output_image.png", 10, 1000, 1, 1, 5, 1, 45
    )
    processor.process()
