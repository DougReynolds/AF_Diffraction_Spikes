# StarSpikesPy (AstroAF Diffraction Spikes) — V2

![AF Diffraction Spikes](/assets/astroAF_logo2.png "AF Diffraction Spikes")

## Overview
StarSpikesPy is a desktop astrophotography tool that adds realistic diffraction spikes to stars while preserving image fidelity and supporting astrophotography-oriented workflows.

Version 2 evolves the original TIFF-only script into a multi-format interactive desktop application with real-time preview, format-specific spike rendering, and improved save handling.

---

## Key Features

### Interactive Desktop UI
- Dual preview panes (Original vs Processed)
- Smooth zoom and pan
- Real-time parameter tuning
- Tooltips for UI controls
- Background-threaded load and processing for responsive interaction

### Diffraction Spike Engine
- Adjustable spike length, thickness, blur, and rotation
- Intelligent star detection
- Per-format spike renderer tuning
- Fast preview-oriented processing workflow

### FIT / FITS Support
- Load FIT / FITS files
- Preserve scientific source data for save workflows
- Preserve FIT metadata / headers where available
- Two FIT save modes:

#### Scientific Mode
- Injects spikes into original FIT data
- Maintains scientific-style output workflow

#### RGB Display Mode
- Saves processed image as RGB FIT cube
- Intended to match the previewed visual result

### Multi-Format Support

#### Input Formats
- FIT / FITS
- TIFF
- PNG
- JPEG

#### Output Formats
- FIT / FITS
- TIFF
- PNG
- JPEG

### Renderer-Aware Defaults
- Format-specific spike renderers
- Renderer-owned tuning defaults
- Consistent type handling across processing and saving
- Cleaner architecture for adding future formats such as XISF

---

## UI Overview

![AF Diffraction Spikes](/assets/ui_view.png "UI Overview")

---

## Installation

### Requirements
- Python 3.11+
- tkinter support

---


### 1. Clone the Repository
```bash
# HTTPS (recommended)
git clone https://github.com/DougReynolds/AF_Diffraction_Spikes.git
cd StarSpikesPy

# OR (SSH, if configured)
# git clone git@github.com:DougReynolds/AF_Diffraction_Spikes.git
```

### Or Download (No Git Required)

Download the latest version as a ZIP:
https://github.com/DougReynolds/AF_Diffraction_Spikes/archive/refs/heads/main.zip

Then extract and open a terminal in the extracted folder.

---

### 2. Create a Virtual Environment (Recommended)

macOS / Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

Windows (PowerShell):
```powershell
python -m venv venv
venv\Scripts\activate
```

---

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

If installing manually, required packages include:

```bash
pip install numpy opencv-python astropy photutils matplotlib pillow scikit-image
```

---

### 4. tkinter Setup

macOS (Homebrew Python):
```bash
brew install python-tk
```

Windows:
- tkinter is included with standard Python installation
- If missing, reinstall Python and ensure "tcl/tk" is selected

---

### 5. Run the Application

```bash
python AF_diffraction_spikes_gui.py
# or
python3 AF_diffraction_spikes_gui.py
```

---

## Troubleshooting

### Missing cv2 (OpenCV)
```text
ModuleNotFoundError: No module named 'cv2'
```
Fix:
```bash
pip install opencv-python
```

---

### Logo Not Loading
If the logo fails to load, ensure:
- You are running from the project root
- The file exists at: `assets/astroAF_logo2.png`

---

### tkinter Errors
- Ensure tkinter is installed (see above)
- On macOS, ensure you are using Homebrew Python with tkinter support

---

### General Tip
Always run the app from the project root directory to ensure relative paths resolve correctly.

## Usage

### 1. Load Image
Supported input formats:
- FIT / FITS
- TIFF
- PNG
- JPG / JPEG

### 2. Adjust Parameters
Use sliders to control:
- Minimum Threshold
- Maximum Threshold
- Spike Length
- Spike Thickness
- Blur Kernel
- Blur Strength
- Rotation Angle

Hover over the info icons for details on each setting.

### 3. Process
- Generates diffraction spikes on detected stars
- Updates processed preview
- Maintains responsive workflow while processing in the background

### 4. Save
Supported output formats:
- FIT / FITS
- TIFF
- PNG
- JPEG

Notes:
- TIFF is recommended for general processed-image workflows
- FIT supports scientific and RGB display save modes

---

## Notes
- FIT files are commonly monochrome in astrophotography workflows
- TIFF is typically the best non-FIT output format for processed images
- Renderer-specific defaults are used internally for format-aware behavior
- Every image is different; parameter tuning is expected and part of normal use

---

## Architecture Notes
Version 2 includes major internal improvements:
- Type handling centralized through a shared image type utility
- Format-specific renderers for FIT, TIFF, PNG, and JPEG
- Shared base spike rendering logic for consistent behavior
- Format-specific save handlers
- Cleaner extension path for future formats

---

## Support
If you like this project, consider supporting development:

<a href="https://www.buymeacoffee.com/AstroAF" target="_blank">
<img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;">
</a>

---

## License
MIT License

---

## Author
Douglas Reynolds
🌐 https://astroaf.space  
📺 https://youtube.com/@AstroAF

---