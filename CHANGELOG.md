

# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog
https://keepachangelog.com/en/1.0.0/

---

## [2.0.0] - 2026-03-21

### 🚀 Added
- Full interactive desktop UI
- Dual image preview (input + processed)
- Zoom and pan support (mouse + trackpad)
- Tooltip help system for all controls
- Animated loading and processing indicators
- Star count estimation
- Multi-format input support (FIT, TIFF, PNG, JPG)
- Multi-format output support (FIT, TIFF, PNG, JPG)

### 🧪 FIT Enhancements
- Scientific FIT support (preserve original data)
- Metadata (header) preservation
- Dual FIT save modes:
  - Scientific (mono, astro-correct)
  - RGB display (3-plane FIT cube)

### ⚡ Performance
- Background threading for image loading
- Background threading for processing
- Non-blocking UI (no freezing)
- Faster rendering pipeline

### 🛠️ Changed
- Migrated from script-based tool to full GUI application
- Replaced static processing flow with real-time preview workflow

### 🐛 Fixed
- Zoom behavior scaling container incorrectly
- Pan/zoom targeting wrong container
- FIT saving losing metadata
- FIT saving forcing grayscale unintentionally
- TIFF save issues with OpenCV
- UI state not resetting on new image load
- Loading indicator not animating

---

## [1.0.0] - Initial Release

### Added
- Basic diffraction spike generation
- TIFF input/output support
- GUI with parameter controls
