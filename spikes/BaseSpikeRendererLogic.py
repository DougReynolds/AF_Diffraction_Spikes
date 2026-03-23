import numpy as np
import cv2
import math

# Shared parameter keys
PARAM_SPIKE_LENGTH_MULTIPLIER = "spike_length_multiplier"
PARAM_SPIKE_THICKNESS_MULTIPLIER = "spike_thickness_multiplier"
PARAM_BLUR_KERNEL_SIZE = "blur_kernel_size"
PARAM_BLUR_MULTIPLIER = "blur_multiplier"
PARAM_ROTATION_ANGLE = "rotation_angle"


class BaseSpikeRendererLogic:
    """
    Shared rendering logic for diffraction spikes.

    IMPORTANT:
    - This class contains NO policy (no thresholds, no flux scaling rules)
    - All policy must be provided by the calling renderer
    """

    # *********************TUNING MODEL OVERVIEW*************************#
    # Spike size is computed as:
    #   (BASE + SCALE * flux_norm) * (MULT_BASE + MULT_SCALE * slider_value)
    #
    # Where:
    #   - BASE: minimum spike size (floor)
    #   - SCALE: how much star brightness (flux_norm) increases size
    #   - MULT_BASE: default strength at slider = 0
    #   - MULT_SCALE: how strongly the UI slider affects the result
    #
    # Slider relationship:
    #   - PARAM_SPIKE_LENGTH_MULTIPLIER and PARAM_SPIKE_THICKNESS_MULTIPLIER
    #     are user-controlled sliders (typically 0–1 range)
    #   - MULT_BASE defines the baseline when slider is at default
    #   - MULT_SCALE defines sensitivity (higher = more aggressive response)
    #
    # Bit depth modes:
    #   - LOW: PNG/JPG (display images)
    #   - HIGH16: 16-bit TIFF (semi-linear)
    #   - HIGH32: FIT / float TIFF (scientific / linear)
    #
    # Goal:
    #   Achieve perceptual parity across formats while allowing stronger
    #   response for high dynamic range data.
    # *******************************************************************#

    # Length scaling constants (LOW bit depth)
    LENGTH_BASE_LOW = 2  # minimum spike length
    LENGTH_SCALE_LOW = 26  # how much flux increases length
    LENGTH_MULT_BASE_LOW = 3  # default multiplier baseline
    LENGTH_MULT_SCALE_LOW = 1.3  # slider sensitivity

    # Length scaling constants (HIGH16 bit depth)
    LENGTH_BASE_HIGH16 = 3  # minimum spike length (16-bit)
    LENGTH_SCALE_HIGH16 = 22  # flux-to-length scaling (moderate)
    LENGTH_MULT_BASE_HIGH16 = 1.8  # stronger default vs low
    LENGTH_MULT_SCALE_HIGH16 = 1.8  # slider sensitivity (moderate)

    # Length scaling constants (HIGH32 bit depth)
    LENGTH_BASE_HIGH32 = 3  # minimum spike length (32-bit/FIT)
    LENGTH_SCALE_HIGH32 = 28  # flux-to-length scaling (strong)
    LENGTH_MULT_BASE_HIGH32 = 2.2  # strongest default
    LENGTH_MULT_SCALE_HIGH32 = 2.0  # highest slider sensitivity

    # Thickness scaling constants (LOW bit depth)
    THICK_BASE_LOW = 1.0  # minimum thickness
    THICK_SCALE_LOW = 1.2  # flux-to-thickness scaling
    THICK_MULT_BASE_LOW = 1.5  # default multiplier baseline
    THICK_MULT_SCALE_LOW = 1.3  # slider sensitivity

    # Thickness scaling constants (HIGH16 bit depth)
    THICK_BASE_HIGH16 = 1.0  # minimum thickness (16-bit)
    THICK_SCALE_HIGH16 = 2.0  # moderate thickness growth
    THICK_MULT_BASE_HIGH16 = 1.3  # slightly stronger default
    THICK_MULT_SCALE_HIGH16 = 1.7  # moderate slider sensitivity

    # Thickness scaling constants (HIGH32 bit depth)
    THICK_BASE_HIGH32 = 1.0  # minimum thickness (32-bit/FIT)
    THICK_SCALE_HIGH32 = 2.4  # strongest thickness growth
    THICK_MULT_BASE_HIGH32 = 1.5  # strong default thickness
    THICK_MULT_SCALE_HIGH32 = 1.95  # highest slider sensitivity

    # Blur tuning constants
    BLUR_KERNEL_SCALE = 3.5  # amplifies slider impact on kernel size
    BLUR_SIGMA_SCALE = 3  # amplifies blur strength (sigma)

    def _render_common(
        self,
        image,
        sources,
        input_path,
        *,
        is_fits,
        threshold,
        flux_boost,
        bit_depth_mode,
    ):
        print("PARAMS IN RENDER:", self.params)
        image_disp = np.ascontiguousarray(image.copy())

        if image_disp.ndim == 3 and image_disp.shape[2] == 4:
            image_disp = image_disp[:, :, :3]
        elif image_disp.ndim == 2:
            image_disp = cv2.cvtColor(image_disp, cv2.COLOR_GRAY2RGB)

        h, w = image_disp.shape[:2]

        scale_ss = 2
        overlay_ss = cv2.resize(
            image_disp, (w * scale_ss, h * scale_ss), interpolation=cv2.INTER_LINEAR
        )

        if overlay_ss.ndim == 3 and overlay_ss.shape[2] == 4:
            overlay_ss = overlay_ss[:, :, :3]

        max_flux = np.max(sources["flux"]) if len(sources) > 0 else 1.0

        for s in sources[:1000]:
            x = int(s["xcentroid"] * scale_ss)
            y = int(s["ycentroid"] * scale_ss)

            if x < 0 or x >= w * scale_ss or y < 0 or y >= h * scale_ss:
                continue

            flux_ref = (
                np.percentile(sources["flux"], 99) if len(sources) > 10 else max_flux
            )

            flux_norm = float(s["flux"]) / float(flux_ref) if flux_ref > 0 else 0.0
            flux_norm = min(flux_norm, 1.0)
            flux_norm = min(1.0, flux_norm * flux_boost)

            if flux_norm < threshold:
                continue

            if is_fits:
                length = int(
                    (5 + 30 * flux_norm)
                    * (1.26 + 2.0 * self.params[PARAM_SPIKE_LENGTH_MULTIPLIER])
                )
            else:
                # Tune these values for decent default result estimate
                if bit_depth_mode == "high32":
                    length = int(
                        (self.LENGTH_BASE_HIGH32 + self.LENGTH_SCALE_HIGH32 * flux_norm)
                        * (
                            self.LENGTH_MULT_BASE_HIGH32
                            + self.LENGTH_MULT_SCALE_HIGH32
                            * self.params[PARAM_SPIKE_LENGTH_MULTIPLIER]
                        )
                    )
                elif bit_depth_mode == "high16":
                    length = int(
                        (self.LENGTH_BASE_HIGH16 + self.LENGTH_SCALE_HIGH16 * flux_norm)
                        * (
                            self.LENGTH_MULT_BASE_HIGH16
                            + self.LENGTH_MULT_SCALE_HIGH16
                            * self.params[PARAM_SPIKE_LENGTH_MULTIPLIER]
                        )
                    )
                else:
                    length = int(
                        (self.LENGTH_BASE_LOW + self.LENGTH_SCALE_LOW * flux_norm)
                        * (
                            self.LENGTH_MULT_BASE_LOW
                            + self.LENGTH_MULT_SCALE_LOW
                            * self.params[PARAM_SPIKE_LENGTH_MULTIPLIER]
                        )
                    )

            if length < 3:
                continue

            if is_fits:
                thickness = max(
                    1,
                    int(
                        (1 + 3 * flux_norm)
                        * (1.26 + 2.0 * self.params[PARAM_SPIKE_THICKNESS_MULTIPLIER])
                    ),
                )
            else:
                # Tune these values for decent default result estimate

                if bit_depth_mode == "high32":
                    thickness = max(
                        1,
                        int(
                            (
                                self.THICK_BASE_HIGH32
                                + self.THICK_SCALE_HIGH32 * flux_norm
                            )
                            * (
                                self.THICK_MULT_BASE_HIGH32
                                + self.THICK_MULT_SCALE_HIGH32
                                * self.params[PARAM_SPIKE_THICKNESS_MULTIPLIER]
                            )
                        ),
                    )
                elif bit_depth_mode == "high16":
                    thickness = max(
                        1,
                        int(
                            (
                                self.THICK_BASE_HIGH16
                                + self.THICK_SCALE_HIGH16 * flux_norm
                            )
                            * (
                                self.THICK_MULT_BASE_HIGH16
                                + self.THICK_MULT_SCALE_HIGH16
                                * self.params[PARAM_SPIKE_THICKNESS_MULTIPLIER]
                            )
                        ),
                    )
                else:
                    thickness = max(
                        1,
                        int(
                            (self.THICK_BASE_LOW + self.THICK_SCALE_LOW * flux_norm)
                            * (
                                self.THICK_MULT_BASE_LOW
                                + self.THICK_MULT_SCALE_LOW
                                * self.params[PARAM_SPIKE_THICKNESS_MULTIPLIER]
                            )
                        ),
                    )
            angle_rad = math.radians(self.params[PARAM_ROTATION_ANGLE])
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)

            dx = length * cos_a
            dy = length * sin_a

            dx_p = -length * sin_a
            dy_p = length * cos_a

            roi_radius = max(8, int(length * scale_ss * 1.5))
            x0 = max(0, x - roi_radius)
            x1_roi = min(w * scale_ss, x + roi_radius + 1)
            y0 = max(0, y - roi_radius)
            y1_roi = min(h * scale_ss, y + roi_radius + 1)

            roi_h = y1_roi - y0
            roi_w = x1_roi - x0

            if roi_h <= 1 or roi_w <= 1:
                continue

            x_local = x - x0
            y_local = y - y0

            spike_mask = np.zeros((roi_h, roi_w), dtype=np.float32)

            cv2.line(
                spike_mask,
                (x_local, y_local),
                (int(x_local + dx), int(y_local + dy)),
                1.0,
                thickness,
                lineType=cv2.LINE_AA,
            )
            cv2.line(
                spike_mask,
                (x_local, y_local),
                (int(x_local - dx), int(y_local - dy)),
                1.0,
                thickness,
                lineType=cv2.LINE_AA,
            )
            cv2.line(
                spike_mask,
                (x_local, y_local),
                (int(x_local + dx_p), int(y_local + dy_p)),
                1.0,
                thickness,
                lineType=cv2.LINE_AA,
            )
            cv2.line(
                spike_mask,
                (x_local, y_local),
                (int(x_local - dx_p), int(y_local - dy_p)),
                1.0,
                thickness,
                lineType=cv2.LINE_AA,
            )

            k_star = max(
                3, int(self.params[PARAM_BLUR_KERNEL_SIZE] * self.BLUR_KERNEL_SCALE)
            )
            if k_star % 2 == 0:
                k_star += 1

            sigma_star = max(
                0.5, self.params[PARAM_BLUR_MULTIPLIER] * self.BLUR_SIGMA_SCALE
            )
            spike_mask = cv2.GaussianBlur(spike_mask, (k_star, k_star), sigma_star)

            yy_roi, xx_roi = np.indices((roi_h, roi_w))
            dx_roi = xx_roi - x_local
            dy_roi = yy_roi - y_local
            r = np.sqrt(dx_roi * dx_roi + dy_roi * dy_roi)

            r_norm = r / (length * scale_ss + 1e-6)
            falloff = np.exp(-2.0 * r_norm)
            spike_mask *= falloff

            if is_fits:
                intensity = 150 * (0.6 + 0.8 * flux_norm)
            else:
                intensity = 135 * (0.55 + 0.7 * flux_norm)

            spike_rgb = np.repeat(spike_mask[:, :, np.newaxis], 3, axis=2)
            roi = overlay_ss[y0:y1_roi, x0:x1_roi].astype(np.float32)
            roi = np.clip(roi + (spike_rgb * intensity), 0, 255)
            overlay_ss[y0:y1_roi, x0:x1_roi] = roi.astype(np.uint8)

        k_opt = max(
            3, int(self.params[PARAM_BLUR_KERNEL_SIZE] * self.BLUR_KERNEL_SCALE)
        )
        if k_opt % 2 == 0:
            k_opt += 1

        sigma_opt = max(0.3, self.params[PARAM_BLUR_MULTIPLIER] * self.BLUR_SIGMA_SCALE)
        overlay_ss = cv2.GaussianBlur(overlay_ss, (k_opt, k_opt), sigma_opt)

        overlay = cv2.resize(overlay_ss, (w, h), interpolation=cv2.INTER_AREA)

        k = int(self.params[PARAM_BLUR_KERNEL_SIZE] * self.BLUR_KERNEL_SCALE)
        if k % 2 == 0:
            k += 1

        if k > 1 and self.params[PARAM_BLUR_MULTIPLIER] > 0:
            overlay = cv2.GaussianBlur(
                overlay,
                (k, k),
                self.params[PARAM_BLUR_MULTIPLIER] * (self.BLUR_SIGMA_SCALE * 0.5),
            )

        mask = np.any(overlay != image_disp, axis=2)

        alpha = 0.85

        for c in range(3):
            image_disp[..., c] = np.where(
                mask,
                (overlay[..., c] * alpha + image_disp[..., c] * (1 - alpha)).astype(
                    np.uint8
                ),
                image_disp[..., c],
            )

        return image_disp

    # Preset intensity multipliers
    PRESET_MILD = 0.75
    PRESET_MEDIUM = 1.0
    PRESET_HOT = 1.35

    def apply_preset(self, preset: str):
        """
        Adjust current params based on preset intensity.
        Presets scale length and thickness multipliers only.
        """
        if preset == "mild":
            scale = self.PRESET_MILD
        elif preset == "hot":
            scale = self.PRESET_HOT
        else:
            scale = self.PRESET_MEDIUM

        # Apply scaling to user-controlled multipliers
        self.params[PARAM_SPIKE_LENGTH_MULTIPLIER] *= scale
        self.params[PARAM_SPIKE_THICKNESS_MULTIPLIER] *= scale
