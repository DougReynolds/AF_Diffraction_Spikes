# StarSpikesPy (AstroAF Diffraction Spikes) — V2

![AF Diffraction Spikes](/assets/astroAF_logo2.png "AstroAF Diffraction Spikes")

## 🚀 Overview
StarSpikesPy is a desktop astrophotography tool that adds realistic diffraction spikes to stars while preserving scientific image integrity.

Version 2 transforms the original script into a fully interactive application with real-time preview, multi-format support, and astrophotography-aware processing.

---

## ✨ Key Features (V2)

### 🖥️ Interactive Desktop UI
- Dual preview panes (Original vs Processed)
- Smooth zoom and pan (trackpad + mouse)
- Real-time parameter tuning
- Tooltips for every control
- Responsive, non-blocking UI (async processing)

---

### 🎯 Diffraction Spike Engine
- Adjustable spike length, thickness, blur, and rotation
- Intelligent star detection
- Fast processing with near-instant preview
- Designed specifically for astrophotography data

---

### 🧪 Scientific FIT Support (NEW)
- Load FIT / FITS files
- Preserve original scientific data
- Preserve FIT metadata (headers, WCS, etc.)
- Two FIT save modes:

#### 🔬 Scientific Mode (default)
- Injects spikes into original data
- Maintains dynamic range
- Outputs mono FIT (astro-correct)

#### 🎨 RGB Display Mode
- Saves processed image as RGB FIT cube
- Matches visual preview exactly

---

### 🖼️ Multi-Format Support

#### Input Formats
- FIT / FITS
- TIFF
- PNG
- JPEG

#### Output Formats
- FIT / FITS (scientific + RGB modes)
- TIFF (lossless, recommended)
- PNG
- JPEG

---

### ⚡ Performance & UX Enhancements
- Background threading for load + processing
- Animated status indicators (Loading… / Processing…)
- Star count estimation
- Clean state reset between images
- No UI freezing

---

## 📸 UI Overview

![AF Diffraction Spikes](/assets/ui_view.png "UI Overview")

---

## 🛠️ Installation (Development Mode)

### Requirements
- Python 3.11+
- tkinter

Mac (Homebrew):
```
brew install python-tk
```

---

### Dependencies

```
pip install -r requirements.txt
```

---

## ▶️ Run the Application

From the project directory:

```
python3 ImageProcessorGUI.py
```

---

## 📦 Packaging (Coming Soon)

Planned:
- macOS `.app`
- Windows `.exe`
- Installer / DMG distribution

---

## 🧭 Usage

### 1. Load Image
- Supports FIT, TIFF, PNG, JPG

### 2. Adjust Parameters
Use sliders to control:
- Minimum / Maximum Threshold
- Spike Length
- Spike Thickness
- Blur Kernel
- Blur Strength
- Rotation Angle

Hover over the ⓘ icons for detailed explanations.

---

### 3. Process
- Generates diffraction spikes
- Updates preview instantly

---

### 4. Save
- Choose output format (TIFF recommended)
- FIT supports scientific or RGB modes

---

## ⚠️ Notes

- FIT files are typically **monochrome** in astrophotography
- RGB FIT output is for visualization compatibility
- TIFF is the best format for processed image workflows

---

## ❤️ Support

If you like this project, consider supporting development:

<a href="https://www.buymeacoffee.com/AstroAF" target="_blank">
<img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;">
</a>

---

## 📜 License
MIT License

---

## 👤 Author
Douglas Reynolds  
🌐 https://astroaf.space  
📺 https://youtube.com/@AstroAF