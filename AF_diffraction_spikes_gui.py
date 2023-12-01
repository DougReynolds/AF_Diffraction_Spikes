import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import subprocess


class ImageProcessor:
    def __init__(self, input_image, output_image, min_threshold, max_threshold, spike_length_multiplier, spike_thickness_multiplier, blur_kernel_size, blur_multiplier, rotation_angle):
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

    def process(self):
        # Load the image
        image = cv2.imread(self.input_image)

        # Convert the image to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Set thresholds to identify bright regions (stars)
        _, binary_image = cv2.threshold(gray, self.min_threshold, self.max_threshold, cv2.THRESH_BINARY)

        # Apply morphological operations to enhance star detection
        kernel = np.ones((5, 5), np.uint8)
        binary_image = cv2.dilate(binary_image, kernel, iterations=2)

        # Find contours in the binary image
        contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Extract star coordinates and sizes from the contours
        star_data = []
        for contour in contours:
            # Calculate the centroid and area of the contour
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                area = cv2.contourArea(contour)
                star_data.append((cx, cy, area))

        # Parameters for diffraction spikes
        blur_kernel_size = self.blur_kernel_size
        blur_multiplier = self.blur_multiplier

        # Create an alpha channel for blending
        alpha_channel = np.zeros_like(gray)

        # Draw diffraction spikes around detected stars with dynamic parameters
        for (x, y, area) in star_data:
            # Convert decimal coordinates to integers
            x, y = int(round(x)), int(round(y))

            # Adjust spike parameters based on star area or any other relevant metric
            spike_length = max(5, int(np.sqrt(area) * self.spike_length_multiplier))  # Ensure a minimum spike length of 5 pixels
            spike_thickness = max(1, int(np.sqrt(area) * self.spike_thickness_multiplier))  # Ensure thickness is a positive integer

            # Calculate spike endpoints for both vertical and horizontal spikes
            angle_rad = np.radians(self.rotation_angle)
            x1_v, y1_v = x, y - spike_length
            x2_v, y2_v = x, y + spike_length
            x1_h, y1_h = x - spike_length, y
            x2_h, y2_h = x + spike_length, y

            # Rotate spike endpoints
            x1_v, y1_v = self.rotate_point((x, y), (x1_v, y1_v), angle_rad)
            x2_v, y2_v = self.rotate_point((x, y), (x2_v, y2_v), angle_rad)
            x1_h, y1_h = self.rotate_point((x, y), (x1_h, y1_h), angle_rad)
            x2_h, y2_h = self.rotate_point((x, y), (x2_h, y2_h), angle_rad)

            # Draw vertical and horizontal spikes on the alpha channel
            cv2.line(alpha_channel, (x1_v, y1_v), (x2_v, y2_v), 255, spike_thickness)
            cv2.line(alpha_channel, (x1_h, y1_h), (x2_h, y2_h), 255, spike_thickness)

        # Apply Gaussian blur to the alpha channel (only on the spikes)
        blur_kernel_size = int(blur_kernel_size * blur_multiplier)
        blur_kernel_size = blur_kernel_size + 1 if blur_kernel_size % 2 == 0 else blur_kernel_size
        alpha_channel = cv2.GaussianBlur(alpha_channel, (blur_kernel_size, blur_kernel_size), 0)

        # Resize the original image to match the dimensions of the spikes image
        image = cv2.resize(image, (alpha_channel.shape[1], alpha_channel.shape[0]), interpolation=cv2.INTER_LINEAR)

        # Blend the images by adding weighted channels
        result_image = cv2.addWeighted(image, 1, cv2.cvtColor(alpha_channel, cv2.COLOR_GRAY2BGR), 0.5, 0)

        # Save the result
        self.processed_image = result_image
        cv2.imwrite(self.output_image, result_image)

        return result_image

    def rotate_point(self, center, point, angle_rad):
        """Rotate a point around a center."""
        x, y = point
        cx, cy = center
        new_x = int(cx + (x - cx) * np.cos(angle_rad) - (y - cy) * np.sin(angle_rad))
        new_y = int(cy + (x - cx) * np.sin(angle_rad) + (y - cy) * np.cos(angle_rad))
        return new_x, new_y

    def save(self):
        # Read the bit depth from the input image
        input_info = cv2.imread(self.input_image, cv2.IMREAD_UNCHANGED)
        bit_depth = input_info.dtype.itemsize * 8  # Calculate bit depth based on item size

        # Save the processed image with the same bit depth
        cv2.imwrite(self.output_image, self.processed_image, [cv2.IMWRITE_TIFF_COMPRESSION, 1, cv2.IMWRITE_TIFF_XDPI, 300, cv2.IMWRITE_TIFF_YDPI, 300, cv2.IMWRITE_PNG_BILEVEL, bit_depth])

class ImageProcessorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AstroAF - AF Diffraction Spikes")
        self.root.minsize(width=900, height=700)
        
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

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageProcessorGUI(root)
    root.mainloop()
