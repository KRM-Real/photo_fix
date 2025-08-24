import io, os
from dataclasses import dataclass
from typing import Tuple, Optional
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
import gradio as gr
from rembg import remove
import cv2
from skimage import restoration, filters
import warnings
warnings.filterwarnings("ignore")

# ---- Try to import MediaPipe; fall back gracefully if unavailable ----
try:
    import mediapipe as mp
    _HAVE_MP = True
except Exception:
    mp = None
    _HAVE_MP = False

# ---- Try to import HuggingFace models; fall back gracefully if unavailable ----
try:
    from transformers import pipeline
    from diffusers import StableDiffusionInpaintPipeline
    import torch
    _HAVE_HF = True
    device = "cuda" if torch.cuda.is_available() else "cpu"
except Exception:
    _HAVE_HF = False
    device = "cpu"

# ---------- ID size presets ----------
PRESETS = {
    "1x1 in @300DPI (300x300)": (300, 300),
    "2x2 in @300DPI (600x600)": (600, 600),
    "35x45 mm @300DPI (413x531)": (413, 531),
    "Custom Square (512x512)": (512, 512),
    "HD Portrait (720x1280)": (720, 1280),
}

# Background colors preset with professional white as default
BG_COLORS = {
    "White": "#FFFFFF",
    "Light Gray": "#F8F9FA", 
    "Blue": "#E3F2FD",
    "Navy": "#1565C0",
    "Black": "#000000",
    "Red": "#FFEBEE",
    "Green": "#E8F5E8",
    "Cream": "#FFF8E1",
}

@dataclass
class FaceBox:
    x: int; y: int; w: int; h: int

def detect_face_box(img: Image.Image) -> FaceBox | None:
    """Return first face box or None (uses MediaPipe if available)."""
    if not _HAVE_MP:
        return None
    mp_face = mp.solutions.face_detection
    rgb = np.array(img.convert("RGB"))
    with mp_face.FaceDetection(model_selection=1, min_detection_confidence=0.5) as fd:
        res = fd.process(rgb)
    if not res.detections:
        return None
    det = res.detections[0]
    bb = det.location_data.relative_bounding_box
    H, W = rgb.shape[:2]
    x, y = max(0, int(bb.xmin * W)), max(0, int(bb.ymin * H))
    w, h = int(bb.width * W), int(bb.height * H)
    return FaceBox(x, y, w, h)

def center_crop_to_aspect(img: Image.Image, ar_t: float) -> Image.Image:
    W, H = img.size
    ar = W / H
    if ar > ar_t:
        newW = int(H * ar_t)
        x1 = (W - newW) // 2
        return img.crop((x1, 0, x1 + newW, H))
    else:
        newH = int(W / ar_t)
        y1 = (H - newH) // 2
        return img.crop((0, y1, W, y1 + newH))

def smart_crop(img: Image.Image, target_size: Tuple[int,int]) -> Image.Image:
    """ID-style crop: head about 75% height with a small top margin."""
    Wt, Ht = target_size
    ar_t = Wt / Ht
    fb = detect_face_box(img)
    if not fb:
        return center_crop_to_aspect(img, ar_t).resize((Wt, Ht), Image.LANCZOS)

    cx, cy = fb.x + fb.w/2, fb.y + fb.h/2
    head_h = fb.h * 1.2  # include hair
    box_h = head_h / 0.75
    box_w = box_h * ar_t
    top_margin = 0.08 * box_h

    x1 = int(cx - box_w/2)
    y1 = int(cy - head_h/2 - top_margin)
    x2 = int(x1 + box_w)
    y2 = int(y1 + box_h)

    W, H = img.size
    x1 = max(0, x1); y1 = max(0, y1)
    x2 = min(W, x2); y2 = min(H, y2)
    if x2 - x1 < 10 or y2 - y1 < 10:
        return center_crop_to_aspect(img, ar_t).resize((Wt, Ht), Image.LANCZOS)

    return img.crop((x1, y1, x2, y2)).resize((Wt, Ht), Image.LANCZOS)

def remove_bg(img: Image.Image, model_name: str = 'u2net') -> Image.Image:
    """Enhanced background removal using rembg with better quality models and advanced post-processing"""
    if img is None:
        return None
    
    try:
        # Convert to RGB if needed for better processing
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Save to bytes with high quality
        b = io.BytesIO()
        img.save(b, format="PNG", quality=95, optimize=True)
        b.seek(0)
        
        # Use rembg with specified model for better quality
        from rembg import remove, new_session
        
        # Try to create session with the specified model
        try:
            session = new_session(model_name)
            cut = remove(b.getvalue(), session=session)
        except Exception as e:
            print(f"Failed to use model {model_name}, falling back to default: {e}")
            # Fallback to basic remove if specific model fails
            cut = remove(b.getvalue())
        
        # Convert result to PIL Image
        result = Image.open(io.BytesIO(cut)).convert("RGBA")
        
        # Advanced post-processing for hair and edge refinement
        result = refine_hair_edges(result, img)
        
        return result
        
    except Exception as e:
        print(f"Background removal failed: {e}")
        # Return original image with white background as fallback
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        return Image.alpha_composite(bg, img.convert("RGBA"))

def refine_hair_edges(cutout_img: Image.Image, original_img: Image.Image) -> Image.Image:
    """Advanced hair edge refinement to remove outlines and improve fine details"""
    try:
        import cv2
        import numpy as np
        
        # Convert images to numpy arrays
        cutout_array = np.array(cutout_img)
        original_array = np.array(original_img.convert("RGBA"))
        
        if len(cutout_array.shape) != 4:  # Ensure RGBA
            return cutout_img
            
        # Extract alpha channel (mask)
        alpha = cutout_array[:, :, 3].astype(np.float32) / 255.0
        
        # Create edge-preserving mask refinement
        # 1. Remove small isolated pixels (noise)
        kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
        alpha_clean = cv2.morphologyEx((alpha * 255).astype(np.uint8), cv2.MORPH_OPEN, kernel_small)
        alpha_clean = alpha_clean.astype(np.float32) / 255.0
        
        # 2. Apply advanced hair-specific smoothing
        alpha_smooth_raw = cv2.bilateralFilter((alpha_clean * 255).astype(np.uint8), 9, 75, 75)
        alpha_smooth = create_smooth_hair_mask(alpha_smooth_raw).astype(np.float32) / 255.0
        
        # 3. Advanced edge feathering for natural hair transitions
        # Create distance transform for soft edges
        mask_binary = (alpha_smooth > 0.1).astype(np.uint8)
        distance = cv2.distanceTransform(mask_binary, cv2.DIST_L2, 5)
        
        # Apply feathering only to edges (not solid areas)
        edge_map = cv2.Canny((alpha_smooth * 255).astype(np.uint8), 30, 100)  # Lower thresholds for finer hair
        edge_dilated = cv2.dilate(edge_map, np.ones((2, 2), np.uint8), iterations=1)  # Smaller dilation
        
        # Create soft feathering mask with variable radius
        feather_radius = 2  # Smaller radius for finer control
        feather_mask = cv2.GaussianBlur(edge_dilated.astype(np.float32), (feather_radius*2+1, feather_radius*2+1), feather_radius/3)
        feather_mask = feather_mask / 255.0
        
        # Apply feathering to hair areas with reduced intensity
        alpha_feathered = alpha_smooth.copy()
        alpha_feathered = alpha_feathered * (1 - feather_mask * 0.2) + (alpha_smooth * 0.8) * feather_mask
        
        # 4. Remove color fringing/outline by intelligent edge blending
        rgb_channels = cutout_array[:, :, :3].astype(np.float32)
        original_rgb = original_array[:, :, :3].astype(np.float32)
        
        # Detect edge pixels with improved gradient detection
        alpha_gradient_x = cv2.Sobel(alpha_feathered, cv2.CV_64F, 1, 0, ksize=3)
        alpha_gradient_y = cv2.Sobel(alpha_feathered, cv2.CV_64F, 0, 1, ksize=3)
        edge_strength = np.sqrt(alpha_gradient_x**2 + alpha_gradient_y**2)
        
        # More conservative blending to preserve hair color
        blend_factor = np.clip(edge_strength * 0.3, 0, 0.6)  # Reduced blending intensity
        blend_factor = blend_factor[:, :, np.newaxis]
        
        rgb_refined = rgb_channels * (1 - blend_factor) + original_rgb * blend_factor
        
        # 5. Final alpha channel refinement
        # Ensure smooth transitions in semi-transparent areas
        alpha_final = cv2.GaussianBlur(alpha_feathered, (3, 3), 0.5)
        
        # Combine refined RGB with refined alpha
        result_array = np.zeros_like(cutout_array, dtype=np.uint8)
        result_array[:, :, :3] = np.clip(rgb_refined, 0, 255).astype(np.uint8)
        result_array[:, :, 3] = np.clip(alpha_final * 255, 0, 255).astype(np.uint8)
        
        return Image.fromarray(result_array, 'RGBA')
        
    except Exception as e:
        print(f"Hair edge refinement failed, using original cutout: {e}")
        return cutout_img

def remove_bg_only(img: Image.Image, model_quality: str = "Standard") -> Image.Image:
    """Enhanced background removal without cropping - supports multiple quality levels with hair-optimized models"""
    if img is None:
        return None
    
    # Enhanced model mapping with better models for hair detection
    model_map = {
        "Fast": "u2net",
        "Standard": "u2net_human_seg", 
        "High Quality": "u2netp",
        "Portrait": "silueta",
        "Hair Focus": "isnet-general-use",  # Best for fine hair details
        "Product": "u2net_cloth_seg"
    }
    
    model = model_map.get(model_quality, "u2net_human_seg")
    return remove_bg(img, model)

def remove_bg_with_postprocess(img: Image.Image, model_quality: str = "Standard", enhance_edges: bool = True) -> Image.Image:
    """Advanced background removal with post-processing for better quality and hair handling"""
    if img is None:
        return None
    
    # First pass: Remove background with hair-optimized model
    if "hair" in model_quality.lower() or model_quality == "Hair Focus":
        result = remove_bg_only(img, "Hair Focus")
    else:
        result = remove_bg_only(img, model_quality)
    
    if enhance_edges and result is not None:
        # Apply additional edge enhancement
        try:
            import cv2
            import numpy as np
            
            # Convert to numpy array
            img_array = np.array(result)
            
            if len(img_array.shape) == 4:  # RGBA
                # Extract alpha channel
                alpha = img_array[:, :, 3]
                
                # Apply morphological operations to clean up the mask while preserving hair
                # Use smaller kernel for hair preservation
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
                alpha = cv2.morphologyEx(alpha, cv2.MORPH_CLOSE, kernel)
                
                # Apply gentle Gaussian blur for smoother edges without losing hair detail
                alpha = cv2.GaussianBlur(alpha, (2, 2), 0.5)
                
                # Enhance edge contrast for better definition
                alpha = cv2.convertScaleAbs(alpha, alpha=1.2, beta=0)
                
                # Update alpha channel
                img_array[:, :, 3] = alpha
                
                # Convert back to PIL
                result = Image.fromarray(img_array, 'RGBA')
                
                # Apply final hair-specific refinement
                result = refine_hair_edges(result, img)
                
        except Exception as e:
            print(f"Edge enhancement failed, using original result: {e}")
    
    return result

def create_smooth_hair_mask(alpha_channel: np.ndarray) -> np.ndarray:
    """Create ultra-smooth hair mask with anti-aliasing for natural hair edges"""
    try:
        import cv2
        
        # Convert to float for better precision
        alpha_float = alpha_channel.astype(np.float32) / 255.0
        
        # Multi-scale smoothing for different hair thickness
        smooth_fine = cv2.GaussianBlur(alpha_float, (3, 3), 0.5)  # Fine hair
        smooth_medium = cv2.GaussianBlur(alpha_float, (5, 5), 1.0)  # Medium hair
        smooth_coarse = cv2.GaussianBlur(alpha_float, (7, 7), 1.5)  # Coarse hair
        
        # Combine multi-scale results
        alpha_combined = (smooth_fine * 0.5 + smooth_medium * 0.3 + smooth_coarse * 0.2)
        
        # Apply anti-aliasing
        alpha_aa = cv2.bilateralFilter((alpha_combined * 255).astype(np.uint8), 9, 50, 50)
        
        return alpha_aa
        
    except Exception as e:
        print(f"Hair mask smoothing failed: {e}")
        return alpha_channel

def remove_blemishes_basic(img: Image.Image, intensity: float = 0.5) -> Image.Image:
    """Basic blemish removal using image processing techniques"""
    # Convert PIL to OpenCV
    img_array = np.array(img)
    if len(img_array.shape) == 4:  # RGBA
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
    elif len(img_array.shape) == 3:  # RGB
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    # Apply bilateral filter for noise reduction while preserving edges
    smooth = cv2.bilateralFilter(img_array, 15, 80, 80)
    
    # Apply Gaussian blur for smoothing
    blur = cv2.GaussianBlur(img_array, (15, 15), 0)
    
    # Blend original with smoothed version based on intensity
    result = cv2.addWeighted(img_array, 1-intensity, smooth, intensity, 0)
    
    # Convert back to PIL
    result_rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
    return Image.fromarray(result_rgb)

def enhance_skin_tone(img: Image.Image) -> Image.Image:
    """Enhance skin tone and overall image quality"""
    # Enhance color saturation
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(1.1)
    
    # Enhance brightness slightly
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.05)
    
    # Enhance contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.1)
    
    # Apply unsharp mask for sharpening
    img_array = np.array(img)
    sharpened = filters.unsharp_mask(img_array, radius=1, amount=0.5)
    sharpened = (sharpened * 255).astype(np.uint8)
    
    return Image.fromarray(sharpened)

def create_formal_overlay(size: Tuple[int, int], style: str = "suit") -> Image.Image:
    """Create a simple formal attire overlay"""
    w, h = size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    
    # Simple suit overlay - dark rectangle for jacket area
    if style == "suit":
        # Create a basic suit shape (simplified)
        suit_color = (20, 20, 40, 180)  # Dark blue with transparency
        
        # Jacket area (lower 60% of image)
        jacket_top = int(h * 0.4)
        jacket_bottom = h
        jacket_left = int(w * 0.1)
        jacket_right = int(w * 0.9)
        
        # Draw jacket area
        for y in range(jacket_top, jacket_bottom):
            for x in range(jacket_left, jacket_right):
                if x < w and y < h:
                    overlay.putpixel((x, y), suit_color)
        
        # Add tie area
        tie_color = (100, 0, 0, 200)  # Red tie
        tie_width = int(w * 0.08)
        tie_left = (w - tie_width) // 2
        tie_right = tie_left + tie_width
        tie_top = int(h * 0.35)
        tie_bottom = int(h * 0.7)
        
        for y in range(tie_top, tie_bottom):
            for x in range(tie_left, tie_right):
                if x < w and y < h:
                    overlay.putpixel((x, y), tie_color)
    
    return overlay

# --- Enhanced Features with User Control ---
def do_cutout(img: Image.Image, size_label: str, crop_enabled: bool = True):
    """Remove background with optional cropping"""
    if img is None:
        return None
    
    if crop_enabled:
        target = PRESETS[size_label]
        cropped = smart_crop(img, target)
        return remove_bg(cropped)
    else:
        return remove_bg(img)

def smart_background_removal(img: Image.Image, quality: str, enhance_edges: bool, crop_to_size: bool, size_label: str):
    """Enhanced smart background removal with quality control and edge enhancement"""
    if img is None:
        return None
    
    if crop_to_size:
        target = PRESETS[size_label]
        cropped = smart_crop(img, target)
        return remove_bg_with_postprocess(cropped, quality, enhance_edges)
    else:
        return remove_bg_with_postprocess(img, quality, enhance_edges)

def solid_background(img: Image.Image, bg_color: str, size_label: str, crop_enabled: bool = True):
    """Add solid color background with optional cropping using enhanced background removal"""
    if img is None:
        return None
    
    if crop_enabled:
        target = PRESETS[size_label]
        cropped = smart_crop(img, target)
        fg = remove_bg_with_postprocess(cropped, "Standard", True)
        bg = Image.new("RGBA", target, bg_color)
        out = Image.alpha_composite(bg, fg).convert("RGB")
        return out
    else:
        # Use original image size
        fg = remove_bg_with_postprocess(img, "Standard", True)
        target = img.size
        bg = Image.new("RGBA", target, bg_color)
        out = Image.alpha_composite(bg, fg).convert("RGB")
        return out

def gradient_background(img: Image.Image, color1: str, color2: str, size_label: str, crop_enabled: bool = True):
    """Add gradient background with optional cropping using enhanced background removal"""
    if img is None:
        return None
    
    if crop_enabled:
        target = PRESETS[size_label]
        cropped = smart_crop(img, target)
        fg = remove_bg_with_postprocess(cropped, "Standard", True)
    else:
        target = img.size
        cropped = img
        fg = remove_bg_with_postprocess(img, "Standard", True)
    
    # Create gradient background
    w, h = target
    gradient = Image.new("RGBA", target)
    
    # Parse colors
    c1 = tuple(int(color1[i:i+2], 16) for i in (1, 3, 5))
    c2 = tuple(int(color2[i:i+2], 16) for i in (1, 3, 5))
    
    for y in range(h):
        ratio = y / h
        r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
        g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
        b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
        
        for x in range(w):
            gradient.putpixel((x, y), (r, g, b, 255))
    
    out = Image.alpha_composite(gradient, fg).convert("RGB")
    return out

def apply_formal_overlay(img: Image.Image, size_label: str, overlay_style: str, crop_enabled: bool = True):
    """Apply formal attire overlay with optional cropping"""
    if img is None:
        return None
    
    if crop_enabled:
        target = PRESETS[size_label]
        base = smart_crop(img, target).convert("RGBA")
    else:
        target = img.size
        base = img.convert("RGBA")
    
    # Create overlay
    overlay = create_formal_overlay(target, overlay_style)
    
    # Composite overlay onto image
    result = Image.alpha_composite(base, overlay)
    return result.convert("RGB")

def enhance_portrait(img: Image.Image, size_label: str, blemish_intensity: float = 0.5, crop_enabled: bool = True):
    """Enhanced portrait processing with optional cropping"""
    if img is None:
        return None
    
    if crop_enabled:
        target = PRESETS[size_label]
        cropped = smart_crop(img, target)
    else:
        cropped = img
    
    # Remove blemishes
    enhanced = remove_blemishes_basic(cropped, blemish_intensity)
    
    # Enhance skin tone and overall quality
    enhanced = enhance_skin_tone(enhanced)
    
    return enhanced

def professional_edit(img: Image.Image, size_label: str, bg_color: str, 
                     formal_style: str, blemish_intensity: float):
    """Complete professional photo edit pipeline"""
    if img is None:
        return None
    
    # Step 1: Crop and enhance portrait
    enhanced = enhance_portrait(img, size_label, blemish_intensity)
    
    # Step 2: Apply formal overlay
    with_attire = apply_formal_overlay(enhanced, size_label, formal_style)
    
    # Step 3: Remove background and add solid color
    target = PRESETS[size_label]
    fg = remove_bg(Image.fromarray(np.array(with_attire)))
    bg = Image.new("RGBA", target, bg_color)
    final = Image.alpha_composite(bg, fg).convert("RGB")
    
    return final

# Modern, clean CSS for professional UI/UX
custom_css = """
/* Base styles for clean, modern look */
* {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif !important;
}

/* Main container */
.gradio-container {
    max-width: 1400px !important;
    margin: 0 auto !important;
    background: #ffffff !important;
}

/* App background - pure white */
body, .main, .app {
    background: #ffffff !important;
    color: #1a1a1a !important;
}

/* Header section with gradient */
.header-modern {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: white !important;
    padding: 2.5rem 2rem !important;
    margin: -2rem -2rem 2rem -2rem !important;
    border-radius: 0 0 1.5rem 1.5rem !important;
    text-align: center !important;
}

.header-title {
    font-size: 2.5rem !important;
    font-weight: 800 !important;
    margin: 0 0 0.5rem 0 !important;
    text-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
}

.header-subtitle {
    font-size: 1.1rem !important;
    opacity: 0.9 !important;
    margin: 0 0 2rem 0 !important;
}

.feature-grid {
    display: grid !important;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)) !important;
    gap: 1rem !important;
    margin-top: 2rem !important;
}

.feature-card {
    background: rgba(255,255,255,0.15) !important;
    backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    border-radius: 1rem !important;
    padding: 1.5rem !important;
    text-align: center !important;
    transition: transform 0.3s ease !important;
}

.feature-card:hover {
    transform: translateY(-2px) !important;
    background: rgba(255,255,255,0.25) !important;
}

/* Tab styling */
.tab-nav {
    background: #f8fafc !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 1rem !important;
    padding: 0.5rem !important;
    margin: 2rem 0 !important;
}

.tab-item {
    background: transparent !important;
    border: none !important;
    border-radius: 0.75rem !important;
    padding: 1rem 2rem !important;
    font-weight: 600 !important;
    color: #64748b !important;
    transition: all 0.3s ease !important;
}

.tab-item.selected {
    background: #667eea !important;
    color: white !important;
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4) !important;
}

/* Section headers */
.section-header {
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%) !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 1rem !important;
    padding: 2rem !important;
    margin-bottom: 2rem !important;
    text-align: center !important;
}

.section-title {
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    color: #1e293b !important;
    margin: 0 0 0.5rem 0 !important;
}

.section-description {
    color: #64748b !important;
    font-size: 1rem !important;
    margin: 0 !important;
}

/* Card containers */
.content-card {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 1.25rem !important;
    padding: 2rem !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1) !important;
    margin-bottom: 1.5rem !important;
}

/* Upload areas */
.upload-zone {
    background: linear-gradient(135deg, #fafbfb 0%, #f4f6f8 100%) !important;
    border: 2px dashed #cbd5e1 !important;
    border-radius: 1rem !important;
    padding: 3rem 2rem !important;
    text-align: center !important;
    transition: all 0.3s ease !important;
    cursor: pointer !important;
}

.upload-zone:hover {
    border-color: #667eea !important;
    background: linear-gradient(135deg, #f8faff 0%, #f0f4ff 100%) !important;
    transform: translateY(-2px) !important;
}

.upload-icon {
    font-size: 3rem !important;
    color: #94a3b8 !important;
    margin-bottom: 1rem !important;
}

.upload-text {
    font-size: 1.1rem !important;
    font-weight: 600 !important;
    color: #475569 !important;
    margin-bottom: 0.5rem !important;
}

.upload-hint {
    color: #64748b !important;
    font-size: 0.9rem !important;
}

/* Buttons */
.btn-primary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    border: none !important;
    color: white !important;
    border-radius: 0.75rem !important;
    padding: 0.875rem 2rem !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4) !important;
}

.btn-primary:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 20px rgba(102, 126, 234, 0.6) !important;
}

.btn-secondary {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    color: #475569 !important;
    border-radius: 0.75rem !important;
    padding: 0.875rem 2rem !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    transition: all 0.3s ease !important;
}

.btn-secondary:hover {
    background: #f8fafc !important;
    border-color: #667eea !important;
    color: #667eea !important;
    transform: translateY(-1px) !important;
}

/* Form controls */
.form-control {
    border: 1px solid #d1d5db !important;
    border-radius: 0.75rem !important;
    padding: 0.75rem 1rem !important;
    font-size: 1rem !important;
    background: #ffffff !important;
    transition: all 0.3s ease !important;
}

.form-control:focus {
    border-color: #667eea !important;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1) !important;
    outline: none !important;
}

/* Accordion styling */
.accordion {
    border: 1px solid #e2e8f0 !important;
    border-radius: 0.75rem !important;
    overflow: hidden !important;
    margin: 1rem 0 !important;
    background: #ffffff !important;
}

.accordion-header {
    background: #f8fafc !important;
    padding: 1.25rem !important;
    font-weight: 600 !important;
    color: #374151 !important;
    border-bottom: 1px solid #e2e8f0 !important;
    cursor: pointer !important;
}

.accordion-content {
    padding: 1.5rem !important;
    background: #ffffff !important;
}

/* Image containers */
.image-preview {
    border: 1px solid #e2e8f0 !important;
    border-radius: 1rem !important;
    overflow: hidden !important;
    background: #ffffff !important;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05) !important;
}

/* Labels and text */
label {
    font-weight: 600 !important;
    color: #374151 !important;
    font-size: 0.95rem !important;
    margin-bottom: 0.5rem !important;
}

.help-text {
    color: #64748b !important;
    font-size: 0.875rem !important;
    margin-top: 0.25rem !important;
}

/* Quick action cards */
.quick-action {
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%) !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 1rem !important;
    padding: 1.5rem !important;
    text-align: center !important;
    transition: all 0.3s ease !important;
    cursor: pointer !important;
}

.quick-action:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1) !important;
    border-color: #667eea !important;
}

/* Loading states */
.loading {
    opacity: 0.7 !important;
    pointer-events: none !important;
}

/* Mobile responsiveness */
@media (max-width: 768px) {
    .header-modern {
        padding: 2rem 1rem !important;
    }
    
    .header-title {
        font-size: 2rem !important;
    }
    
    .feature-grid {
        grid-template-columns: 1fr !important;
    }
    
    .content-card {
        padding: 1.5rem !important;
    }
}

/* Animation for smooth interactions */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.fade-in {
    animation: fadeIn 0.5s ease-out !important;
}

/* Progress indicators */
.progress {
    background: #f1f5f9 !important;
    border-radius: 0.5rem !important;
    height: 0.5rem !important;
    overflow: hidden !important;
}

.progress-bar {
    background: linear-gradient(90deg, #667eea, #764ba2) !important;
    border-radius: 0.5rem !important;
    transition: width 0.3s ease !important;
}
"""

# --- Clean, Modern UI with Professional Design ---
with gr.Blocks(title="PhotoFix - Professional Photo Editor", css=custom_css, theme=gr.themes.Soft()) as demo:
    # Modern header with gradient background
    gr.HTML("""
    <div class="header-modern">
        <h1 class="header-title">📸 PhotoFix</h1>
        <p class="header-subtitle">Professional Photo Editor with AI-Powered Tools</p>
        <div class="feature-grid">
            <div class="feature-card">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">🎯</div>
                <div style="font-weight: 600;">Background Removal</div>
                <div style="font-size: 0.9rem; opacity: 0.8;">Like remove.bg quality</div>
            </div>
            <div class="feature-card">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">🎨</div>
                <div style="font-weight: 600;">Custom Backgrounds</div>
                <div style="font-size: 0.9rem; opacity: 0.8;">Professional colors</div>
            </div>
            <div class="feature-card">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">✨</div>
                <div style="font-weight: 600;">Enhancement Tools</div>
                <div style="font-size: 0.9rem; opacity: 0.8;">Blemish removal & more</div>
            </div>
            <div class="feature-card">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">👔</div>
                <div style="font-weight: 600;">Formal Attire</div>
                <div style="font-size: 0.9rem; opacity: 0.8;">AI clothing changes</div>
            </div>
        </div>
    </div>
    """)

    with gr.Tab("🎯 Background Removal"):
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("## 🎯 Remove Background\nRemove background without any automatic cropping - just like remove.bg!", elem_classes="content-card")
                
                bg_img = gr.Image(type="pil", label="📤 Upload Your Photo")
                
                with gr.Accordion("⚙️ Enhanced Background Removal Settings", open=True):
                    bg_quality = gr.Dropdown(
                        choices=["Fast", "Standard", "High Quality", "Portrait", "Hair Focus", "Product"],
                        value="Standard",
                        label="🎯 Removal Quality",
                        info="Standard: Best for people | Hair Focus: Best for fine hair details | Product: Best for objects | High Quality: Slower but better"
                    )
                    
                    enhance_edges = gr.Checkbox(
                        value=True,
                        label="✨ Enhance edges (smoother cutouts)",
                        info="Applies post-processing for cleaner edges"
                    )
                    
                    crop_bg = gr.Checkbox(
                        value=False,
                        label="📐 Crop to specific size (off = keep original size)"
                    )
                    bg_size = gr.Dropdown(
                        choices=list(PRESETS.keys()),
                        value="2x2 in @300DPI (600x600)",
                        label="📏 Crop Size (only if cropping enabled)",
                        visible=False
                    )
                    
                    gr.HTML("""
                    <div style="background: #f0f8ff; padding: 10px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #2196F3;">
                        <h4 style="margin: 0 0 8px 0; color: #1976D2;">💡 Hair & Edge Tips:</h4>
                        <ul style="margin: 0; padding-left: 20px; color: #333;">
                            <li><strong>Hair Focus:</strong> Use for photos with fine hair details or complex hair styles</li>
                            <li><strong>Enable Edge Enhancement:</strong> Automatically removes outlines and smooths edges</li>
                            <li><strong>Best Results:</strong> Use high-resolution photos with good lighting</li>
                        </ul>
                    </div>
                    """)
                
                btn_remove_bg = gr.Button("🎯 Remove Background", variant="primary", size="lg")
            
            with gr.Column(scale=1):
                out_bg_removed = gr.Image(type="pil", label="✨ Background Removed")
        
        # Show/hide crop size based on checkbox
        crop_bg.change(
            lambda x: gr.update(visible=x),
            inputs=crop_bg,
            outputs=bg_size
        )
    
    with gr.Tab("🎨 Background Colors"):
        gr.Markdown("### Add solid colors or gradients to your photos")
        
        with gr.Row():
            with gr.Column():
                color_img = gr.Image(type="pil", label="📤 Upload Your Photo")
                
                with gr.Accordion("🎨 Background Options", open=True):
                    bg_type = gr.Radio(
                        choices=["Solid Color", "Gradient"],
                        value="Solid Color",
                        label="Background Type"
                    )
                    
                    # Solid color options
                    with gr.Group(visible=True) as solid_group:
                        preset_color = gr.Dropdown(
                            choices=list(BG_COLORS.keys()),
                            value="White",
                            label="Preset Colors"
                        )
                        custom_color = gr.ColorPicker(value="#FFFFFF", label="Custom Color")
                    
                    # Gradient options
                    with gr.Group(visible=False) as gradient_group:
                        grad_color1 = gr.ColorPicker(value="#FFFFFF", label="Start Color")
                        grad_color2 = gr.ColorPicker(value="#F0F0F0", label="End Color")
                
                with gr.Accordion("📐 Size Options", open=False):
                    crop_color = gr.Checkbox(
                        value=False,
                        label="Crop to specific size"
                    )
                    color_size = gr.Dropdown(
                        choices=list(PRESETS.keys()),
                        value="2x2 in @300DPI (600x600)",
                        label="Output Size",
                        visible=False
                    )
                
                with gr.Row():
                    btn_solid_bg = gr.Button("� Add Solid Background", variant="secondary")
                    btn_gradient_bg = gr.Button("� Add Gradient", variant="secondary")
            
            with gr.Column():
                out_colored_bg = gr.Image(type="pil", label="� Colored Background")
        
        # Show/hide groups based on background type
        def update_bg_groups(bg_type):
            return (
                gr.update(visible=bg_type=="Solid Color"),
                gr.update(visible=bg_type=="Gradient")
            )
        
        bg_type.change(
            update_bg_groups,
            inputs=bg_type,
            outputs=[solid_group, gradient_group]
        )
        
        crop_color.change(
            lambda x: gr.update(visible=x),
            inputs=crop_color,
            outputs=color_size
        )
    
    with gr.Tab("✨ Enhancement Tools"):
        gr.Markdown("### Optional photo enhancement - only when you need it!")
        
        with gr.Row():
            with gr.Column():
                enhance_img = gr.Image(type="pil", label="📤 Upload Your Photo")
                
                with gr.Accordion("✨ Enhancement Options", open=True):
                    enhancement_type = gr.CheckboxGroup(
                        choices=["Remove Blemishes", "Add Formal Attire"],
                        label="Choose Enhancements"
                    )
                    
                    # Blemish removal settings
                    with gr.Group() as blemish_group:
                        blemish_intensity = gr.Slider(
                            minimum=0.0, maximum=1.0, value=0.5,
                            label="Blemish Removal Intensity"
                        )
                    
                    # Formal attire settings
                    with gr.Group() as formal_group:
                        formal_style = gr.Dropdown(
                            choices=["suit", "business", "formal"],
                            value="suit",
                            label="Formal Style"
                        )
                
                with gr.Accordion("📐 Size Options", open=False):
                    crop_enhance = gr.Checkbox(
                        value=False,
                        label="Crop to specific size"
                    )
                    enhance_size = gr.Dropdown(
                        choices=list(PRESETS.keys()),
                        value="2x2 in @300DPI (600x600)",
                        label="Output Size",
                        visible=False
                    )
                
                btn_enhance = gr.Button("✨ Apply Enhancements", variant="primary")
            
            with gr.Column():
                out_enhanced = gr.Image(type="pil", label="✨ Enhanced Photo")
        
        crop_enhance.change(
            lambda x: gr.update(visible=x),
            inputs=crop_enhance,
            outputs=enhance_size
        )
    
    with gr.Tab("🚀 Quick Actions"):
        gr.Markdown("### Common photo editing workflows")
        
        with gr.Row():
            with gr.Column():
                quick_img = gr.Image(type="pil", label="📤 Upload Your Photo")
                
                with gr.Row():
                    btn_quick_id = gr.Button("📋 ID Photo Ready", variant="primary")
                    btn_quick_professional = gr.Button("� Professional Headshot", variant="primary")
                    btn_quick_social = gr.Button("📱 Social Media Ready", variant="secondary")
            
            with gr.Column():
                out_quick = gr.Image(type="pil", label="⚡ Quick Result")
        
        # Quick action functions
        def make_id_photo(img):
            if img is None: return None
            # ID photo: crop + white background
            return solid_background(img, "#FFFFFF", "2x2 in @300DPI (600x600)", crop_enabled=True)
        
        def make_professional(img):
            if img is None: return None
            # Professional: enhance + formal attire + white background
            enhanced = enhance_portrait(img, "2x2 in @300DPI (600x600)", 0.3, crop_enabled=True)
            with_attire = apply_formal_overlay(enhanced, "2x2 in @300DPI (600x600)", "suit", crop_enabled=False)
            return solid_background(with_attire, "#FFFFFF", "2x2 in @300DPI (600x600)", crop_enabled=False)
        
        def make_social_ready(img):
            if img is None: return None
            # Social media: enhanced background removal, keep original size
            return remove_bg_with_postprocess(img, "High Quality", True)
    
    # Event handlers
    def get_bg_color(preset_choice, custom_color):
        return BG_COLORS.get(preset_choice, custom_color)
    
    # Enhanced background removal with edge enhancement
    btn_remove_bg.click(
        smart_background_removal,
        inputs=[bg_img, bg_quality, enhance_edges, crop_bg, bg_size],
        outputs=out_bg_removed
    )
    
    # Background colors
    btn_solid_bg.click(
        lambda img, preset, custom, crop, size: solid_background(
            img, get_bg_color(preset, custom), size, crop
        ),
        inputs=[color_img, preset_color, custom_color, crop_color, color_size],
        outputs=out_colored_bg
    )
    
    btn_gradient_bg.click(
        lambda img, c1, c2, crop, size: gradient_background(
            img, c1, c2, size, crop
        ),
        inputs=[color_img, grad_color1, grad_color2, crop_color, color_size],
        outputs=out_colored_bg
    )
    
    # Enhancement
    def apply_enhancements(img, enhancements, blemish_intensity, formal_style, crop, size):
        if img is None:
            return None
        
        result = img
        
        if "Remove Blemishes" in enhancements:
            result = enhance_portrait(result, size, blemish_intensity, crop)
        
        if "Add Formal Attire" in enhancements:
            result = apply_formal_overlay(result, size, formal_style, crop)
        
        return result
    
    btn_enhance.click(
        apply_enhancements,
        inputs=[enhance_img, enhancement_type, blemish_intensity, formal_style, crop_enhance, enhance_size],
        outputs=out_enhanced
    )
    
    # Quick actions
    btn_quick_id.click(make_id_photo, inputs=quick_img, outputs=out_quick)
    btn_quick_professional.click(make_professional, inputs=quick_img, outputs=out_quick)
    btn_quick_social.click(make_social_ready, inputs=quick_img, outputs=out_quick)

if __name__ == "__main__":
    demo.launch(share=True, debug=False)
