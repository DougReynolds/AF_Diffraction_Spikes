import numpy as np


class ImageTypeUtil:
    @staticmethod
    def get_renderer_for_path(input_path, spike_renderer):
        ext = input_path.lower()

        if ext.endswith(".png"):
            return spike_renderer.png_renderer
        elif ext.endswith((".jpg", ".jpeg")):
            return spike_renderer.jpg_renderer
        elif ext.endswith((".tif", ".tiff")):
            return spike_renderer.tiff_renderer
        elif ext.endswith((".fit", ".fits")):
            return spike_renderer.fit_renderer
        else:
            return spike_renderer.tiff_renderer

    @staticmethod
    def get_image_type(input_path):
        ext = input_path.lower()

        if ext.endswith(".png"):
            return "png"
        elif ext.endswith((".jpg", ".jpeg")):
            return "jpg"
        elif ext.endswith((".tif", ".tiff")):
            return "tiff"
        elif ext.endswith((".fit", ".fits")):
            return "fit"
        else:
            return "tiff"

    def get_bit_depth_mode(image):
        if image.dtype == np.uint8:
            return "low"
        elif image.dtype == np.uint16:
            return "high16"
        elif image.dtype in (np.float32, np.float64):
            return "high32"
        return "low"
