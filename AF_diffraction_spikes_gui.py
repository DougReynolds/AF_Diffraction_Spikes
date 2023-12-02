from ImageProcessor import ImageProcessor
from ImageProcessorGUI import ImageProcessorGUI
import tkinter as tk

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageProcessorGUI(root)
    root.mainloop()