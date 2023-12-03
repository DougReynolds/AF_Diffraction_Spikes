import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import subprocess
from ImageProcessor import ImageProcessor
import cv2

class ImageProcessorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AstroAF - AF Diffraction Spikes")
        self.root.minsize(width=900, height=700)

        # Placeholder for logo image
        self.logo_image = tk.PhotoImage(file="./assets/astroAF_logo2.png")
        
        # Variables for storing user input
        self.input_image_var = tk.StringVar()
        self.output_image_var = tk.StringVar()
        self.min_threshold_var = tk.DoubleVar()
        self.max_threshold_var = tk.DoubleVar()
        self.length_multiplier_var = tk.DoubleVar()
        self.thickness_multiplier_var = tk.DoubleVar()
        self.blur_kernel_size_var = tk.DoubleVar()
        self.blur_multiplier_var = tk.DoubleVar()
        self.rotation_angle_var = tk.DoubleVar()

         # Create and pack widgets
        self.create_widgets()

        # Placeholder images for previews
        self.input_image_preview = ImageTk.PhotoImage(Image.new("RGB", (600, 600), "gray"))
        self.processed_image_preview = ImageTk.PhotoImage(Image.new("RGB", (600, 600), "gray"))

        # Image previews
        self.input_image_label = tk.Label(self.root, image=self.input_image_preview)
        self.input_image_label.grid(row=12, column=1, padx=10, pady=10)
        self.processed_image_label = tk.Label(self.root, image=self.processed_image_preview, cursor="hand2")
        self.processed_image_label.grid(row=12, column=2, padx=10, pady=10)
        self.processed_image_label.bind("<Button-1>", self.open_processed_image)

    def create_widgets(self):
        # Logo
        logo_label = tk.Label(self.root, image=self.logo_image)
        logo_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        tk.Label(self.root, text="Input and Output Files").grid(row=0, column=0, columnspan=4, pady=10)

        # Input Image
        self.add_tooltip(tk.Label(self.root, text="Select Input TIFF Image: ℹ"), "Select the input image for processing.")
        tk.Entry(self.root, textvariable=self.input_image_var, width=30).grid(row=1, column=2)
        tk.Button(self.root, text="Browse", command=self.browse_input_image).grid(row=1, column=3, pady=10)

        # Output Image
        self.add_tooltip(tk.Label(self.root, text="Select/Name Output TIFF Image: ℹ"), "Select or provide a name for the processed output image.")
        tk.Entry(self.root, textvariable=self.output_image_var, width=30).grid(row=2, column=2)
        tk.Button(self.root, text="Browse", command=self.browse_output_image).grid(row=2, column=3, pady=10)

        tk.Label(self.root, text="Diffraction Spikes Configuration").grid(row=3, column=0, columnspan=4, pady=10)

        # Minimum Threshold Slider
        self.add_tooltip(tk.Label(self.root, text="Set Minimum Threshold: ℹ"), "This value sets the lower limit for pixel intensity. \nPixels with intensity values below this threshold are considered \npart of the background and are not classified as stars.")
        tk.Scale(self.root, from_=0, to=255, resolution=1, orient=tk.HORIZONTAL, variable=self.min_threshold_var).grid(row=4, column=2)

        # Maximum Threshold Slider
        self.add_tooltip(tk.Label(self.root, text="Set Maximum Threshold: ℹ"), "This value sets the upper limit for pixel intensity. \nPixels with intensity values above this threshold \nare considered potential stars.")
        tk.Scale(self.root, from_=0, to=255, resolution=1, orient=tk.HORIZONTAL, variable=self.max_threshold_var).grid(row=5, column=2)

        # Spike Length Multiplier Slider
        self.add_tooltip(tk.Label(self.root, text="Set Spike Length Multiplier: ℹ"), "Adjust the length of the diffraction spikes.")
        tk.Scale(self.root, from_=0, to=2, resolution=0.01, orient=tk.HORIZONTAL, variable=self.length_multiplier_var).grid(row=6, column=2)

        # Spike Thickness Multiplier Slider
        self.add_tooltip(tk.Label(self.root, text="Set Spike Thickness Multiplier: ℹ"), "Adjust the thickness of the diffraction spikes.")
        tk.Scale(self.root, from_=0, to=1, resolution=0.01, orient=tk.HORIZONTAL, variable=self.thickness_multiplier_var).grid(row=7, column=2)

        # Blur Kernel Size Slider
        self.add_tooltip(tk.Label(self.root, text="Set Blur Kernel Size: ℹ"), "Set the size of the blur kernel applied to the spikes.")
        tk.Scale(self.root, from_=1, to=50, resolution=2, orient=tk.HORIZONTAL, variable=self.blur_kernel_size_var).grid(row=8, column=2)

        # Blur Multiplier Slider
        self.add_tooltip(tk.Label(self.root, text="Set Blur Multiplier: ℹ"), "Adjust the intensity of the blur applied to the spikes.")
        tk.Scale(self.root, from_=0.1, to=2, resolution=0.01, orient=tk.HORIZONTAL, variable=self.blur_multiplier_var).grid(row=9, column=2)

        # Rotation Angle Slider
        self.add_tooltip(tk.Label(self.root, text="Set Rotation Angle (degrees): ℹ"), "Set the rotation angle for the diffraction spikes.")
        tk.Scale(self.root, from_=0, to=89, resolution=1, orient=tk.HORIZONTAL, variable=self.rotation_angle_var).grid(row=10, column=2)

        # Process Button
        tk.Button(self.root, text="Process and Generate Image", command=self.process_image, height=3, width=30).grid(row=11, column=0, columnspan=4, pady=10)

    def add_tooltip(self, widget, text):
        widget.grid(sticky="w", pady=(0, 10))
        widget.bind("<Enter>", lambda event, text=text: self.show_tooltip(event, text))
        widget.bind("<Leave>", lambda event: self.hide_tooltip())

    def show_tooltip(self, event, text):
        x, y, _, _ = event.widget.bbox("insert")
        x += event.widget.winfo_rootx() + 25
        y += event.widget.winfo_rooty() + 25
        self.tooltip = tk.Toplevel(event.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tooltip, text=text, background="#1c1c1c", foreground="#ffffff", relief="solid", borderwidth=1)
        label.pack()

    def hide_tooltip(self):
        if hasattr(self, "tooltip"):
            self.tooltip.destroy()

    def browse_input_image(self):
        file_path = tk.filedialog.askopenfilename(filetypes=[("Image files", "*.tif")])
        self.input_image_var.set(file_path)
        self.update_input_image_preview(file_path)

    def browse_output_image(self):
        file_path = tk.filedialog.asksaveasfilename(defaultextension=".tif", filetypes=[("TIFF files", "*.tif")])
        self.output_image_var.set(file_path)

    def process_image(self):
        # Get user input
        input_image = self.input_image_var.get()
        output_image = self.output_image_var.get()
        min_threshold = self.min_threshold_var.get()
        max_threshold = self.max_threshold_var.get()
        length_multiplier = self.length_multiplier_var.get()
        thickness_multiplier = self.thickness_multiplier_var.get()
        blur_kernel_size = self.blur_kernel_size_var.get()
        blur_multiplier = self.blur_multiplier_var.get()
        rotation_angle = self.rotation_angle_var.get()

        # Process the image using the provided parameters
        processor = ImageProcessor(input_image, output_image, min_threshold, max_threshold, length_multiplier, thickness_multiplier, blur_kernel_size, blur_multiplier, rotation_angle)
        processed_image = processor.process()
        processor.save()

        # Update processed image preview
        self.update_processed_image_preview(processed_image)

    def update_input_image_preview(self, file_path):
        try:
            img = Image.open(file_path)
            img.thumbnail((300, 200))
            img = ImageTk.PhotoImage(img)
            self.input_image_preview = img
            self.input_image_label.configure(image=self.input_image_preview)
            self.input_image_label.image = self.input_image_preview
        except Exception as e:
            print(f"Error updating input image preview: {e}")

    def update_input_image_preview(self, file_path):
        try:
            img = Image.open(file_path)
            img = self.scale_image(img, width=600)  # Added this line
            img = ImageTk.PhotoImage(img)
            self.input_image_preview = img
            self.input_image_label.configure(image=self.input_image_preview)
            self.input_image_label.image = self.input_image_preview
        except Exception as e:
            print(f"Error updating input image preview: {e}")

    def update_processed_image_preview(self, processed_image):
        try:
            img = Image.fromarray(cv2.cvtColor(processed_image, cv2.COLOR_BGR2RGB))
            img = self.scale_image(img, width=600)  # Added this line
            img = ImageTk.PhotoImage(img)
            self.processed_image_preview = img
            self.processed_image_label.configure(image=self.processed_image_preview)
            self.processed_image_label.image = self.processed_image_preview
        except Exception as e:
            print(f"Error updating processed image preview: {e}")

    # Added the following method
    def scale_image(self, img, width):
        aspect_ratio = img.width / img.height
        new_height = int(width / aspect_ratio)
        return img.resize((width, new_height))

    def open_processed_image(self, event):
        output_image_path = self.output_image_var.get()
        try:
            # Use subprocess to open the image with the default viewer
            subprocess.run(["open", output_image_path], check=True)
        except Exception as e:
            print(f"Error opening processed image: {e}")
