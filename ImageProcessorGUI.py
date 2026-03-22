# NOTE: requires `tifffile` for full TIFF compatibility
def _load_image_any_format(path):
    from PIL import Image
    import numpy as np
    import cv2

    # Try PIL first
    try:
        return Image.open(path)
    except Exception:
        pass

    # If TIFF, go straight to tifffile (avoid OpenCV header errors)
    if path.lower().endswith((".tif", ".tiff")):
        try:
            import tifffile as tiff

            data = tiff.imread(path)

            # Normalize to 8-bit for display (handle float/uint32 safely)
            data = data.astype(np.float32)
            data_min = np.min(data)
            data_max = np.max(data)

            if data_max > data_min:
                data = (data - data_min) / (data_max - data_min)
            else:
                data = np.zeros_like(data)

            data = (data * 255).astype(np.uint8)

            if data.ndim == 2:
                return Image.fromarray(data)
            elif data.ndim == 3:
                return Image.fromarray(data)
        except Exception as e:
            raise RuntimeError(f"Unsupported TIFF format: {path} ({e})")

    # Non-TIFF: try OpenCV
    img_cv = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img_cv is None:
        raise RuntimeError(f"Unsupported image format: {path}")

    # Normalize to 8-bit for display
    img_cv = cv2.normalize(img_cv, None, 0, 255, cv2.NORM_MINMAX)
    img_cv = img_cv.astype(np.uint8)

    # Convert BGR->RGB if needed
    if len(img_cv.shape) == 3:
        img_cv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)

    return Image.fromarray(img_cv)


import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import subprocess
from ImageProcessor import ImageProcessor
from astropy.io import fits
from astropy.visualization import simple_norm
import matplotlib.pyplot as plt
import cv2
import numpy as np
import io
import threading


class ImageProcessorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AstroAF - AF Diffraction Spikes")
        self.root.minsize(width=900, height=700)

        # Set background color to black
        self.root.configure(bg="black")

        # Placeholder for logo image
        self.logo_image = tk.PhotoImage(file="./assets/astroAF_logo2.png")

        # Variables for storing user input
        self.input_image_var = tk.StringVar()
        self.output_image_var = tk.StringVar()
        # Set sensible default starting values (QoL improvement)
        self.min_threshold_var = tk.DoubleVar(value=25)
        self.max_threshold_var = tk.DoubleVar(value=255)
        self.length_multiplier_var = tk.DoubleVar(value=1.2)
        self.thickness_multiplier_var = tk.DoubleVar(value=0.35)
        self.blur_kernel_size_var = tk.DoubleVar(value=15)
        self.blur_multiplier_var = tk.DoubleVar(value=0.4)
        self.rotation_angle_var = tk.DoubleVar(value=30)

        # Star count display (QoL)
        self.star_count_var = tk.StringVar(value="Stars detected: -")

        # Loading/status indicator for processing
        self.status_var = tk.StringVar(value="")
        self._processing_job = None
        self._processing_dots = 0

        # Loading indicator for image loading
        self.load_status_var = tk.StringVar(value="")
        self._load_job = None
        self._load_dots = 0

        # debounce handle for slider updates
        self._star_count_job = None
        self._star_count_thread = None

        # Placeholder images for previews
        self.input_image_preview = ImageTk.PhotoImage(
            Image.new("RGB", (600, 600), "gray")
        )
        self.processed_image_preview = ImageTk.PhotoImage(
            Image.new("RGB", (600, 600), "gray")
        )

        # Create and pack widgets
        self.create_widgets()

        self.zoom_scale = 1.0
        self.pan_start = None
        self.pan_offset = [0, 0]
        self.pan_last_global = None

    def create_widgets(self):
        # Main layout frames
        control_frame = tk.Frame(self.root, bg="black")
        control_frame.grid(row=0, column=0, sticky="nsw", padx=20, pady=10)

        preview_frame = tk.Frame(self.root, bg="black")
        preview_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        row = 0

        def section(title):
            nonlocal row
            tk.Label(
                control_frame,
                text=title,
                bg="black",
                fg="white",
                font=("Helvetica", 16, "bold"),
            ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(15, 5))
            row += 1

        def slider(label, var, frm, to, res, help_text=None, command=None):
            nonlocal row

            # Label
            tk.Label(
                control_frame,
                text=label,
                bg="black",
                fg="white",
                font=("Helvetica", 12),
            ).grid(row=row, column=0, sticky="w")

            # Frame to hold slider + info button
            slider_frame = tk.Frame(control_frame, bg="black")
            slider_frame.grid(row=row, column=1, pady=2, sticky="ew")

            # Slider
            tk.Scale(
                slider_frame,
                from_=frm,
                to=to,
                resolution=res,
                orient=tk.HORIZONTAL,
                variable=var,
                command=command,
                bg="black",
                fg="white",
                troughcolor="#2a2a2a",
                highlightthickness=0,
                activebackground="#00d4ff",
                length=170,
            ).pack(side="left")

            # Info button (tooltip trigger)
            if help_text:
                info_btn = tk.Label(
                    slider_frame,
                    text="ⓘ",
                    bg="black",
                    fg="#00d4ff",
                    font=("Helvetica", 12, "bold"),
                    cursor="hand2",
                )
                info_btn.pack(side="left", padx=(5, 0))

                info_btn.bind("<Enter>", lambda e, t=help_text: self.show_tooltip(e, t))
                info_btn.bind("<Leave>", lambda e: self.hide_tooltip())

            row += 1

        # Logo
        tk.Label(control_frame, image=self.logo_image, bg="black").grid(
            row=row, column=0, columnspan=2, sticky="w"
        )
        row += 1

        # Instructions label (UX)
        tk.Label(
            control_frame,
            text="Tip: Scroll to zoom, click-drag to pan",
            bg="black",
            fg="#aaaaaa",
            font=("Helvetica", 10),
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(5, 10))
        row += 1

        # Files
        section("Files")
        tk.Button(
            control_frame, text="Load Image", command=self.browse_input_image
        ).grid(row=row, column=0, columnspan=2, sticky="ew", pady=5)
        row += 1
        tk.Label(
            control_frame,
            textvariable=self.load_status_var,
            bg="black",
            fg="#00d4ff",
            font=("Helvetica", 14),
        ).grid(row=row, column=0, columnspan=2, pady=(0, 10))
        row += 1

        # Detection
        section("Detection")
        slider(
            "Min Threshold",
            self.min_threshold_var,
            0,
            255,
            1,
            "Lower bound for star detection. Increase to ignore faint stars and noise.",
            self.schedule_star_count,
        )

        slider(
            "Max Threshold",
            self.max_threshold_var,
            0,
            255,
            1,
            "Upper bound for star detection. Rarely needs adjustment unless bright stars are clipping.",
            self.schedule_star_count,
        )

        tk.Label(
            control_frame,
            textvariable=self.star_count_var,
            bg="black",
            fg="cyan",
            font=("Helvetica", 14),
        ).grid(row=row, column=0, columnspan=2, pady=5)
        row += 1

        # Spike Shape
        section("Spike Shape")
        slider(
            "Length",
            self.length_multiplier_var,
            0,
            2,
            0.01,
            "Controls how far diffraction spikes extend from each star. Higher values create longer spikes.",
        )
        slider(
            "Thickness",
            self.thickness_multiplier_var,
            0,
            1,
            0.01,
            "Controls the width of the spike core. Higher values produce bolder, more prominent spikes.",
        )
        slider(
            "Rotation",
            self.rotation_angle_var,
            0,
            89,
            1,
            "Rotates the spike pattern. Useful for aligning spikes to match telescope orientation.",
        )

        # Optical
        section("Optical")
        slider(
            "Blur Kernel",
            self.blur_kernel_size_var,
            1,
            50,
            2,
            "Controls how far the glow spreads from each spike. Larger values create wider halos.",
        )
        slider(
            "Blur Strength",
            self.blur_multiplier_var,
            0.1,
            2,
            0.01,
            "Controls how soft or sharp the spikes appear. Higher values create smoother, more diffuse spikes.",
        )

        # Process button
        tk.Button(
            control_frame,
            text="PROCESS",
            command=self.process_image,
            font=("Helvetica", 16),
            bg="#00d4ff",
        ).grid(row=row, column=0, columnspan=2, pady=20, sticky="ew")

        # Save button (disabled until first process)
        self.save_btn = tk.Button(
            control_frame,
            text="Save Image",
            command=self.save_image,
            state="disabled",
            bg="#2a2a2a",
            fg="black",
            disabledforeground="#888888",
            activebackground="#00d4ff",
            font=("Helvetica", 12),
        )
        self.save_btn.grid(
            row=row + 1, column=0, columnspan=2, pady=(5, 10), sticky="ew"
        )

        # Status/Loading indicator under PROCESS and Save buttons
        tk.Label(
            control_frame,
            textvariable=self.status_var,
            bg="black",
            fg="#00d4ff",
            font=("Helvetica", 14),
        ).grid(row=row + 2, column=0, columnspan=2, pady=(5, 10))

        # Preview (fixed-size frames)
        input_container = tk.Frame(preview_frame, width=600, height=600, bg="black")
        input_container.pack(side="left", padx=10, pady=10)
        input_container.pack_propagate(False)

        self.input_image_view = tk.Canvas(
            input_container, width=600, height=600, bg="black", highlightthickness=0
        )
        self.input_image_view.pack(fill="both", expand=True)
        self.input_image_id = self.input_image_view.create_image(
            300, 300, image=self.input_image_preview
        )
        self.input_placeholder = self.input_image_view.create_text(
            300, 300, text="Load Image", fill="#555555", font=("Helvetica", 22, "bold")
        )

        processed_container = tk.Frame(preview_frame, width=600, height=600, bg="black")
        processed_container.pack(side="left", padx=10, pady=10)
        processed_container.pack_propagate(False)

        self.processed_image_view = tk.Canvas(
            processed_container, width=600, height=600, bg="black", highlightthickness=0
        )
        self.processed_image_view.pack(fill="both", expand=True)
        self.processed_image_id = self.processed_image_view.create_image(
            300, 300, image=self.processed_image_preview
        )
        self.processed_placeholder = self.processed_image_view.create_text(
            300, 300, text="Load Image", fill="#555555", font=("Helvetica", 22, "bold")
        )
        self.processed_image_view.bind("<Button-1>", self.open_processed_image)
        # Guidance label (centered under previews using grid)
        guidance_label = tk.Label(
            self.root,
            text="Scroll to zoom • Click-drag to pan",
            bg="black",
            fg="white",
            font=("Helvetica", 12),
        )
        guidance_label.grid(row=1, column=1, sticky="ew", pady=(0, 10))

        # Enable zoom + pan
        for widget in [self.input_image_view, self.processed_image_view]:
            widget.bind("<MouseWheel>", self.zoom_image)
            widget.bind("<ButtonPress-1>", self.start_pan)
            widget.bind("<B1-Motion>", self.do_pan)

    def zoom_image(self, event):
        # Normalize delta
        if hasattr(event, "delta") and event.delta != 0:
            delta = event.delta
        elif hasattr(event, "num"):
            delta = 120 if event.num == 4 else -120
        else:
            return

        # Direct, pan-like zoom (proportional to input, minimal shaping)
        zoom_sensitivity = 0.0025  # controls overall responsiveness

        self.zoom_scale += -delta * zoom_sensitivity

        # Hard stop: do not allow zoom-out below original display scale
        self.zoom_scale = max(1.0, min(self.zoom_scale, 3.0))

        # If we hit minimum zoom, reset pan (no panning when fully zoomed out)
        if self.zoom_scale <= 1.0:
            self.pan_offset = [0, 0]

        self.apply_transform()

    def start_pan(self, event):
        # Use global coordinates to avoid widget-relative jumps
        self.pan_last_global = (event.x_root, event.y_root)

    def do_pan(self, event):
        if self.pan_last_global is None:
            return

        # Use global coordinates (prevents "container offset" feel)
        dx = event.x_root - self.pan_last_global[0]
        dy = event.y_root - self.pan_last_global[1]

        pan_speed = 1.0

        self.pan_offset[0] += dx * pan_speed
        self.pan_offset[1] += dy * pan_speed

        self.pan_last_global = (event.x_root, event.y_root)

        self.apply_transform()

    def apply_transform(self):
        try:
            # Input image (zoom display image)
            if hasattr(self, "input_image_display"):
                img = self.input_image_display
                zoomed = img.resize(
                    (
                        int(img.width * self.zoom_scale),
                        int(img.height * self.zoom_scale),
                    )
                )

                img_tk = ImageTk.PhotoImage(zoomed)
                self.input_image_view.itemconfig(self.input_image_id, image=img_tk)
                self.input_image_view.image = img_tk

                # Constrain pan to image bounds
                max_x = max(0, (zoomed.width - 600) // 2)
                max_y = max(0, (zoomed.height - 600) // 2)

                self.pan_offset[0] = max(-max_x, min(max_x, self.pan_offset[0]))
                self.pan_offset[1] = max(-max_y, min(max_y, self.pan_offset[1]))

                self.input_image_view.coords(
                    self.input_image_id,
                    300 + self.pan_offset[0],
                    300 + self.pan_offset[1],
                )

            # Processed image
            if hasattr(self, "processed_image_display"):
                img = self.processed_image_display
                zoomed = img.resize(
                    (
                        int(img.width * self.zoom_scale),
                        int(img.height * self.zoom_scale),
                    )
                )

                img_tk = ImageTk.PhotoImage(zoomed)
                self.processed_image_view.itemconfig(
                    self.processed_image_id, image=img_tk
                )
                self.processed_image_view.image = img_tk

                # Constrain pan to image bounds
                max_x = max(0, (zoomed.width - 600) // 2)
                max_y = max(0, (zoomed.height - 600) // 2)

                self.pan_offset[0] = max(-max_x, min(max_x, self.pan_offset[0]))
                self.pan_offset[1] = max(-max_y, min(max_y, self.pan_offset[1]))

                self.processed_image_view.coords(
                    self.processed_image_id,
                    300 + self.pan_offset[0],
                    300 + self.pan_offset[1],
                )

        except Exception as e:
            print(f"Zoom error: {e}")

    def show_tooltip(self, event, text):
        x, y, _, _ = event.widget.bbox("insert")
        x += event.widget.winfo_rootx() + 300
        x += event.widget.winfo_rootx() + 25
        y += event.widget.winfo_rooty() + 25
        self.tooltip = tk.Toplevel(event.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            self.tooltip,
            text=text,
            background="#111111",
            foreground="#ffffff",
            relief="solid",
            borderwidth=1,
            font=("Helvetica", 11),
            padx=8,
            pady=6,
            wraplength=250,
            justify="left",
        )
        label.pack()

    def hide_tooltip(self):
        if hasattr(self, "tooltip"):
            self.tooltip.destroy()

    def browse_input_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[
                ("FITS files", "*.fit *.fits"),
                ("TIFF files", "*.tif *.tiff"),
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg *.jpeg"),
                ("All files", "*.*"),
            ]
        )
        if not file_path:
            return

        # Start loading animation (force immediate visible text)
        self._load_dots = 1
        self.load_status_var.set("Loading")
        self.root.update_idletasks()
        self.animate_loading()

        # Run load in background thread
        threading.Thread(
            target=self._load_image_worker, args=(file_path,), daemon=True
        ).start()
        return

    def animate_loading(self):
        dots = "." * (self._load_dots % 4)
        self.load_status_var.set(f"Loading{dots}")
        self._load_dots += 1
        self._load_job = self.root.after(500, self.animate_loading)

    def stop_loading(self):
        if self._load_job:
            self.root.after_cancel(self._load_job)
            self._load_job = None
        self.load_status_var.set("")

    def _prepare_input_image(self, file_path):
        import numpy as np
        import cv2

        # FITS path
        if file_path.lower().endswith((".fit", ".fits")):
            with fits.open(file_path) as hdul:
                image_data = hdul[0].data

            # Normalize for display
            if image_data.dtype != np.uint8:
                image_data = cv2.normalize(image_data, None, 0, 255, cv2.NORM_MINMAX)
                image_data = image_data.astype(np.uint8)

            if image_data.ndim == 2:
                img = Image.fromarray(image_data)
            elif image_data.ndim == 3 and image_data.shape[0] == 3:
                img = Image.fromarray(np.transpose(image_data, (1, 2, 0)))
            else:
                raise ValueError("Unsupported FIT format")

        else:
            # Standard image path (TIFF/PNG/JPG)
            img = _load_image_any_format(file_path)

        img = self.scale_image(img, width=600)
        return img

    def _load_image_worker(self, file_path):
        try:
            img = self._prepare_input_image(file_path)
            self.root.after(0, lambda: self._load_image_apply(file_path, img))
        except Exception as e:
            print(f"Load error: {e}")
            self.root.after(0, self._load_image_complete)

    def _load_image_apply(self, file_path, img):
        try:
            self.input_image_var.set(file_path)
            self.input_image_display = img.copy()
            img_tk = ImageTk.PhotoImage(img)
            self.input_image_preview = img_tk
            self.input_image_view.itemconfig(self.input_image_id, image=img_tk)
            self.input_image_view.image = img_tk
            self.input_image_view.itemconfig(self.input_placeholder, state="hidden")
            self.processed_image_view.itemconfig(
                self.processed_placeholder, text="Process Image", state="normal"
            )
        finally:
            self._load_image_complete()

    def _load_image_complete(self):
        self.zoom_scale = 1.0
        self.pan_offset = [0, 0]

        # Reset processed preview (reuse existing logic)
        try:
            if hasattr(self, "processed_image_display"):
                del self.processed_image_display

            blank = ImageTk.PhotoImage(Image.new("RGB", (600, 600), "gray"))
            self.processed_image_preview = blank
            self.processed_image_view.itemconfig(self.processed_image_id, image=blank)
            self.processed_image_view.image = blank

            self.processed_image_view.itemconfig(
                self.processed_placeholder, text="Process Image", state="normal"
            )

            if hasattr(self, "save_btn"):
                self.save_btn.config(state="disabled")

        except Exception as e:
            print(f"Reset processed preview error: {e}")

        # Keep the loading indicator alive until star counting completes
        threading.Thread(target=self._update_star_count_worker, daemon=True).start()

    def _update_star_count_worker(self):
        try:
            input_image = self.input_image_var.get()
            if not input_image:
                self.root.after(
                    0, lambda: self._finish_loading_with_star_count("Stars detected: -")
                )
                return

            processor = ImageProcessor(
                input_image,
                None,
                self.min_threshold_var.get(),
                self.max_threshold_var.get(),
                1.0,
                1.0,
                3,
                0.1,
                0,
            )

            # FITS path
            if input_image.lower().endswith((".fit", ".fits")):
                with fits.open(input_image) as hdul:
                    image_data = hdul[0].data
            else:
                # Use robust loader (handles PixInsight TIFF)
                pil_img = _load_image_any_format(input_image)
                image_data = np.array(pil_img)
                if image_data.ndim == 3:
                    image_data = np.mean(image_data, axis=2)

            sources = processor.detect_stars(image_data)

            try:
                count = len(sources) if sources is not None else 0
            except Exception:
                count = 0

            self.root.after(
                0,
                lambda: self._finish_loading_with_star_count(
                    f"Stars detected: {count}"
                ),
            )

        except Exception as e:
            print(f"[StarCount ERROR] {e}")
            self.root.after(
                0,
                lambda: self._finish_loading_with_star_count("Stars detected: error"),
            )

    def _finish_loading_with_star_count(self, text):
        self.star_count_var.set(text)
        self.stop_loading()

    def schedule_star_count(self, event=None):
        # cancel any pending job
        if self._star_count_job is not None:
            self.root.after_cancel(self._star_count_job)

        # schedule new one (150ms debounce)
        self._star_count_job = self.root.after(150, self.update_star_count)

    def update_star_count(self, event=None):
        try:
            input_image = self.input_image_var.get()
            if not input_image:
                return

            # Lightweight detection only
            processor = ImageProcessor(
                input_image,
                None,
                self.min_threshold_var.get(),
                self.max_threshold_var.get(),
                1.0,  # dummy
                1.0,  # dummy
                3,  # dummy
                0.1,  # dummy
                0,  # dummy
            )

            # Load image directly (avoid relying on processor internals)
            if input_image.lower().endswith((".fit", ".fits")):
                with fits.open(input_image) as hdul:
                    image_data = hdul[0].data
            else:
                pil_img = _load_image_any_format(input_image)
                image_data = np.array(pil_img)
                if image_data.ndim == 3:
                    image_data = np.mean(image_data, axis=2)

            # Run detection only
            sources = processor.detect_stars(image_data)

            if sources is None:
                count = 0
            else:
                try:
                    count = len(sources)
                except Exception:
                    count = 0

            self.star_count_var.set(f"Stars detected: {count}")

        except Exception as e:
            print(f"[StarCount ERROR] {e}")
            self.star_count_var.set("Stars detected: error")

    def process_image(self):
        # Start animation
        self._processing_dots = 1
        self.animate_processing()

        # Run processing in background thread
        threading.Thread(target=self._process_image_worker, daemon=True).start()

    def _process_image_worker(self):
        try:
            input_image = self.input_image_var.get()
            output_image = self.output_image_var.get()
            min_threshold = self.min_threshold_var.get()
            max_threshold = self.max_threshold_var.get()
            length_multiplier = self.length_multiplier_var.get()
            thickness_multiplier = self.thickness_multiplier_var.get()
            blur_kernel_size = self.blur_kernel_size_var.get()
            blur_multiplier = self.blur_multiplier_var.get()
            rotation_angle = self.rotation_angle_var.get()

            processor = ImageProcessor(
                input_image,
                output_image,
                min_threshold,
                max_threshold,
                length_multiplier,
                thickness_multiplier,
                blur_kernel_size,
                blur_multiplier,
                rotation_angle,
            )

            processed_image = processor.process()
            processor.save()

            self.root.after(0, self._process_image_complete, processed_image)

        except Exception as e:
            print(f"Processing error: {e}")
            self.root.after(0, self._process_image_complete, None)

    def _process_image_complete(self, processed_image):
        # Stop animation
        if self._processing_job:
            self.root.after_cancel(self._processing_job)
            self._processing_job = None

        self.status_var.set("")

        if processed_image is not None:
            self.update_processed_image_preview(processed_image)

        # Enable Save button once processed image is available
        if hasattr(self, "save_btn") and processed_image is not None:
            self.save_btn.config(state="normal")

    def save_image(self):
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[
                    ("PNG files", "*.png"),
                    ("TIFF files", "*.tif *.tiff"),
                    ("JPEG files", "*.jpg"),
                    ("FITS files", "*.fit *.fits"),
                    ("All files", "*.*"),
                ],
            )

            if not file_path:
                return

            processor = ImageProcessor(
                self.input_image_var.get(),
                file_path,
                self.min_threshold_var.get(),
                self.max_threshold_var.get(),
                self.length_multiplier_var.get(),
                self.thickness_multiplier_var.get(),
                self.blur_kernel_size_var.get(),
                self.blur_multiplier_var.get(),
                self.rotation_angle_var.get(),
            )

            if hasattr(self, "processed_image_display"):
                processor.processed_image = self.processed_image_display
                processor.save()

        except Exception as e:
            print(f"Save error: {e}")

    def animate_processing(self):
        dots = "." * (self._processing_dots % 4)
        self.status_var.set(f"Processing{dots}")
        self._processing_dots += 1
        self._processing_job = self.root.after(500, self.animate_processing)

    # update_input_image_preview is no longer called from loading flow

    def plot_to_image(self):
        buf = io.BytesIO()
        plt.savefig(
            buf, format="png", bbox_inches="tight", pad_inches=0, transparent=True
        )
        buf.seek(0)
        return Image.open(buf)

    def update_processed_image_preview(self, processed_image):
        try:
            img = Image.fromarray(processed_image)
            img = self.scale_image(img, width=600)
            self.processed_image_display = img.copy()

            # Re-apply current zoom/pan transform instead of resetting view
            self.apply_transform()

            # Hide processed placeholder
            self.processed_image_view.itemconfig(
                self.processed_placeholder, state="hidden"
            )
        except Exception as e:
            print(f"Error updating processed image preview: {e}")

    def plot_to_photo_image(self, plt):
        plt_buf = io.BytesIO()
        plt.savefig(
            plt_buf, format="png", bbox_inches="tight", pad_inches=0, transparent=True
        )
        plt_buf.seek(0)
        return ImageTk.PhotoImage(Image.open(plt_buf))

    def scale_image(self, img, width):
        aspect_ratio = img.size[0] / img.size[1]
        new_height = int(width / aspect_ratio)
        return img.resize((width, new_height))

    def open_processed_image(self, event):
        output_image_path = self.output_image_var.get()
        try:
            # Use subprocess to open the image with the default viewer
            subprocess.run(["open", output_image_path], check=True)
        except Exception as e:
            print(f"Error opening processed image: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageProcessorGUI(root)
    root.mainloop()
