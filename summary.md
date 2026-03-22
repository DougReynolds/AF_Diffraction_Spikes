

# StarSpikes V2 – Current State Summary

## Overview
StarSpikes V2 is a working diffraction spike rendering pipeline for astrophotography images. The system detects stars, filters out nebula/false positives, and applies physically-inspired diffraction spikes with user-adjustable parameters via a GUI.

---

## ✅ Completed / Working

### 1. Environment & Execution
- Python environment (pyenv + venv) stable
- All required libraries installed and working:
  - numpy, opencv, astropy, photutils, matplotlib, pillow
- GUI launches and processes images successfully

---

### 2. Star Detection Pipeline
- Background modeling via `Background2D`
- High-pass filtering applied to suppress nebula (Gaussian subtraction)
- Detection via `DAOStarFinder`
- Converted to luminance for more consistent detection

### Filtering (multi-stage)
- Sharpness filter
- Flux percentile filter
- Peak percentile filter
- Roundness constraint

### Result
- Reliable star-only detection
- Nebula largely excluded from detections
- Detection sensitivity controllable via UI

---

### 3. Diffraction Spike Rendering
- 4-spike pattern (corrected from 8)
- Rotation angle implemented and working
- Spike properties:
  - Length scaled by star brightness (flux)
  - Thickness scaled by brightness
- Rendering uses overlay + masked blending (prevents nebula blowout)

---

### 4. Image Processing / Display
- FITS → normalized → display-safe image pipeline
- Proper handling of:
  - dtype conversion (uint16 → uint8)
  - channel layout (C,H,W → H,W,C)
  - OpenCV compatibility (contiguous arrays)

---

### 5. Preview System
- Large preview implemented using matplotlib
- Uses percentile stretch (1–99%) to avoid oversaturation
- Supports zoom and pan via matplotlib toolbar
- Current improvement: should be triggered via GUI button instead of auto-popup

---

## ⚠️ Known Limitations / Next Work

### 1. Spike Appearance (Primary Remaining Work)
Current spikes are:
- Geometrically correct
- Visually "drawn" (uniform intensity)

Needed:
- Radial intensity falloff along spike
- Optional tapering / soft edges
- More physically realistic diffraction behavior

---

### 2. Detection Tuning
- High-pass filter kernel size strongly affects detection
- Percentile thresholds can be too aggressive
- Need better balance or adaptive thresholds

---

### 3. GUI / UX Improvements
Planned:
- Add "Large Preview" button
- Optional auto-preview toggle
- Potential embedded zoom/pan preview (instead of matplotlib window)

---

### 4. Output
- FITS saving not yet implemented
- No PNG/JPG export yet

---

## 🧠 Key Milestones Achieved

- Transitioned from raw detection → **nebula-suppressed star detection**
- Transitioned from debug rendering → **physically plausible spike overlay**
- Established stable processing pipeline and UI controls

---

## 🚀 Next Steps (Priority Order)

1. Implement spike intensity falloff (highest impact visual improvement)
2. Add GUI-controlled large preview button
3. Fine-tune detection thresholds (possibly adaptive)
4. Add output saving (FITS + PNG)

---

## Status

✔ Functional V2 pipeline  
✔ Visually usable results  
➡ Entering refinement / realism phase