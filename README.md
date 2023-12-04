# Diffraction Spikes

![AF Diffraction Spikes](/assets/astroAF_logo2.png "AF Diffraction Spikes")

## Description:
This script adds diffraction spikes to stars in astrophotography images.

**This script only processes TIFF input images and only processes TIFF output images.**

Add an image to be processed and provide an output file name.

![AF Diffraction Spikes](/assets/ui_view.png "AF Diffraction Spikes")

## Donations
If you like this software and would like to help support development and maintenance of this project, please consider buying me a coffee

<a href="https://www.buymeacoffee.com/AstroAF" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>

## Installation Requirements:
Computer running at least Python 3.11 with tkinter support

% `brew install python-tk`

For Windows installation, please refer to the Python page:
https://www.python.org/downloads/windows/

For other platforms:
https://www.python.org/download/other/

### Dependencies

tkinter: If you are using Homebrew (otherwise tkinter is a standard python lib): % `brew install python-tk`

cv2: % `pip3 install opencv-python`

numpy: % `pip3 install numpy`

Pillow: % `pip3 install Pillow`


## Installation:
Download the zip file for this script or check out the project with git.

Un-archive the zip file into a directory of your choice

Assuming your python installation is run using `python3`, issue the following command from within the directory you installed the script.  How you run python is dependent upon your platform and installation.  For example on Mac with Homebrew installed Python 3, your python command may be `python3`.  On other platforms it may just be `python`.

% `python3 AF_diffraction_spikes_gui.py`

## Usage
### Selecting Input and Output
Select your input file (to be processed) and processed output file name.  For processed output file you can also choose an existing file.  This is convenient when you are working with an image and testing configuration changes to the same output file.  When choosing an existing output file, the file will be overwritten upon each processing run.

![Seleting Input and Output Image Selections](/assets/input_output.png "Input and Output Image Selections")

### Configuring Parameters
Within the AF Diffraction Spikes GUI you will find a series of numeric sliders which are used for assigning parameter vaules for specific calculations.  Please hover over each information icon ( <sup>i</sup> ) next to the control label for more information on each parameter.

![Setting Configuration Parameters](/assets/configuration.png "Setting Configuration Parameters")

1. Set Minium Threshold: This value sets the lower limit for pixel intensity. Pixels with intensity values below this threshold are considered part of the background and are not classified as stars.
2. Set Maximum Threshold: This value sets the upper limit for pixel intensity. Pixels with intensity values above this threshold are considered potential stars.
3. Set Spike Length Multiplier: Adjust the length of the diffraction spikes.
4. Set Spike Thickness Multiplier: Adjust the thickness of the diffraction spikes.
5. Set Blur Kernel Size: Set the size of the blur kernel applied to the spikes.
6. Set Blur Multiplier: Adjust the intensity of the blur applied to the spikes.
7. Set Rotation Angle: Set the rotation angle for the diffraction spikes.
8. Process and Generate Image: Clicking this button will process and generate an image with diffraction spike configurations applied.
9. Preview Images: The left preview is gthe original image entered into the input image selection.  The right preview image is the result of processing diffraction spikes.
**Note** You may click on the output image preview to view a larger image.

## General Note
AF Diffraction Spikes configuration can take a lot of trial and error.  Every image is different and requires unique sets of paramegters.  So, with that said, there is no one right way.  Work with the sliders and experiment.  Preview your output image as often as you like, it is created nearly instantaneously.

## License
[MIT](./LICENSE)

## Credit
AF Diffraction Spikes written by: Douglas Reynolds

doug [at] astroaf [dot] space

https://astroaf.space

https://Youtube.com/@AstroAF
