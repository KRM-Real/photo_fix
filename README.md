# PhotoFix - Professional Photo Editor

A PhotoRoom-like application with AI-powered photo editing capabilities.

## Features

### 🎯 Core Features
- **Smart Background Removal**: AI-powered background removal using rembg
- **Custom Backgrounds**: Solid colors, gradients, and custom colors
- **Blemish Removal**: AI-enhanced skin smoothing and blemish removal
- **Formal Attire Overlay**: Add professional suits and formal wear
- **Portrait Enhancement**: Skin tone enhancement and quality improvement

### 🚀 Professional Pipeline
- One-click professional photo transformation
- Combines all features into a single workflow
- Perfect for ID photos, professional headshots, and social media

## Installation

1. Make sure you have Python 3.8+ installed
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the application:
```bash
python Photofix.py
```

The app will open in your web browser with a shareable link.

### Individual Tools Tab
- **Background Removal**: Remove background and create transparent PNG
- **Solid Background**: Add solid color backgrounds
- **Gradient Background**: Create gradient backgrounds
- **Formal Attire**: Add professional suit overlays
- **Portrait Enhancement**: Remove blemishes and enhance skin

### Professional Pipeline Tab
- Upload your photo
- Choose output size and background color
- Select formal style and enhancement intensity
- Get a complete professional photo in one click

## Supported Image Sizes
- 1x1 inch @300DPI (300x300px)
- 2x2 inch @300DPI (600x600px) 
- 35x45mm @300DPI (413x531px)
- Custom Square (512x512px)
- HD Portrait (720x1280px)

## Background Colors
- White, Black, Blue, Red, Green, Gray, Navy, Cream
- Custom color picker for any color
- Gradient backgrounds with two-color blending

## Technical Details

### AI Models Used
- **rembg**: Background removal using deep learning
- **MediaPipe**: Face detection for smart cropping
- **OpenCV**: Image processing for blemish removal
- **scikit-image**: Advanced image enhancement

### Image Processing Pipeline
1. Smart face detection and cropping
2. Background removal using AI
3. Blemish removal with bilateral filtering
4. Skin tone enhancement
5. Formal attire overlay application
6. Background color/gradient application

## Future Enhancements

The app is designed to be easily extensible with:
- HuggingFace transformer models for advanced AI features
- Real-ESRGAN for super-resolution
- CodeFormer for face restoration
- Stable Diffusion for background generation

## Requirements

See `requirements.txt` for complete dependency list.

## License

Open source - feel free to modify and extend!
