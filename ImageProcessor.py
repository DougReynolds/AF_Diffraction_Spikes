import cv2
import numpy as np

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
            self.draw_spikes(alpha_channel, (x1_v, y1_v), (x2_v, y2_v), spike_thickness)
            self.draw_spikes(alpha_channel, (x1_h, y1_h), (x2_h, y2_h), spike_thickness)

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

    def draw_spikes(self, alpha_channel, start_point, end_point, thickness):
        spike_length = len(start_point)  # Assuming start_point and end_point have the same length
        points_x = np.linspace(start_point[0], end_point[0], num=spike_length * 2)
        points_y = np.linspace(start_point[1], end_point[1], num=spike_length * 2)

        # Calculate the gradient for a smooth transition
        gradient = np.linspace(0, 1, num=spike_length * 4)

        # Iterate over the points and draw spikes on the alpha channel
        length = len(points_x) // 2  # Half the length for symmetric drawing
        for i in range(length * 2):  # Iterate up to the total length
            alpha_value = int(255 * gradient[i])  # Scale the gradient to the alpha channel range
            cv2.line(alpha_channel, (int(points_x[i]), int(points_y[i])), (int(points_x[length * 2 - i - 1]), int(points_y[length * 2 - i - 1])), alpha_value, thickness)

    def rotate_point(self, center, point, angle_rad):
        # Rotate a point around a center
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
