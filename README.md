# AstroAF Diffraction Spikes — V2

![AstroAF Diffraction Spikes](/assets/astroAF_diffraction_spikes_social_logo.jpg "AstroAF Diffraction Spikes")

## Table of Contents
- [Overview](#overview)
- [Key Features](#key-features)
- [UI Overview](#ui-overview)
- [Installation (Recommended)](#installation-recommended)
- [Build From Source](#build-from-source)
- [Troubleshooting](#troubleshooting)
- [Usage](#usage)
- [Notes](#notes)
- [Architecture Notes](#architecture-notes)
- [Support](#support)
- [License](#license)
- [Author](#author)

---

## Overview
AstroAF Diffraction Spikes is a desktop astrophotography tool designed to add realistic, physically-inspired diffraction spikes to stars while preserving the integrity of the original image. It is intended for astrophotographers who want to achieve diffraction spike effects without using physical modifications such as wires or other attachments over the objective lens.

Built for astrophotographers, the application provides an interactive workflow for enhancing images with diffraction spikes without compromising detail in nebulae, galaxies, or background structures. Version 2 introduces a fully interactive UI, fast preview workflow, significant performance improvements, and a robust processing pipeline that adapts to multiple image formats and bit depths.

The tool intelligently detects stars using background modeling, high-pass filtering, and flux-based filtering to isolate true point sources while rejecting diffuse structures. This ensures diffraction spikes are applied accurately and consistently across a wide range of astrophotography targets.


With support for FIT/FITS, TIFF, PNG, and JPEG, AstroAF Diffraction Spikes bridges scientific workflows and visual processing, making it suitable for both data-driven imaging and final presentation output.

For high bit-depth workflows (16-bit and 32-bit), processing is performed using the original image data, ensuring output images retain the same resolution and fidelity as the input files.

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
- Preserves FITS header data

#### RGB Display Mode
- Saves processed image as RGB FIT cube
- Intended to match the previewed visual result

### Multi-Format Support

#### Input Formats
- FIT / FITS
- TIFF / TIF
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

The application is divided into two primary preview panes and a configuration panel:

- **Original Preview (Left):** Displays the loaded source image. Supports zoom and pan for detailed inspection.
- **Processed Preview (Right):** Displays the output with diffraction spikes applied. Updates after processing to reflect current parameter settings.
- **Preview Panes Zoom and Pan:** Zoom with your mouse wheel or trackpad and click and drag to pan.
- **Left Pane Controls:** File loading, processing, and save actions.

![Main Application UI](/assets/ui_view.png "Main Application UI")

---

### Configuration Panel

The configuration panel provides control over detection and rendering parameters:

- **Loaded Filename:** Displays the currently loaded image file name for reference.
- **Load Button:** Opens a file dialog to select an image for processing.
- **Loading Indicator:** Displays status while an image is being loaded.

- **Detection Minimum:** Controls the lower threshold for star detection.
- **Detection Maximum:** Controls the upper threshold and filtering behavior for detected stars.

- **Spike Shape Controls:**
  - **Length:** Adjusts the length of diffraction spikes.
  - **Thickness:** Controls the width of spikes.
  - **Rotation:** Rotates the spike orientation.

- **Presets:** Quickly apply predefined spike styles (mild, medium, or hot).

- **Optical Controls:**
  - **Blur Kernel:** Controls the size of the blur kernel applied to spikes.
  - **Blur Strength:** Adjusts the intensity of the blur effect.

- **Process Button:** Runs star detection and spike rendering.
- **Processing Indicator:** Displays status while processing is running.

- **Save Image:** Saves the processed output to the selected format.
- **Scientific FITS Option:** Enables saving FIT output with preserved scientific data and headers.

- **Tooltips:** All controls include tooltips for additional guidance.

![Configuration Panel](/assets/configuration.png "Configuration Controls")

---

## Installation (Recommended)

Download the latest release from GitHub:
https://github.com/DougReynolds/AF_Diffraction_Spikes/releases

### macOS
- Download the `.app` bundle from the latest release
- Open the app (you may need to allow it in System Settings → Privacy & Security)

### Windows
- Download the `.exe` from the latest release
- Double-click to run (no additional setup required)

No Python installation or dependency setup is required when using the installer.

---

## Build From Source

### Requirements
- Python 3.11+
- tkinter support

---


### 1. Clone the Repository
```bash
# HTTPS (recommended)
git clone https://github.com/DougReynolds/AF_Diffraction_Spikes.git
cd AF_Diffraction_Spikes

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
python3 -m venv .venv
source .venv/bin/activate
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

![AF Diffraction Spikes](/assets/astroAF_logo2.png "AF Diffraction Spikes")

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