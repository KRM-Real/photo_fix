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

# Background colors preset
BG_COLORS = {
    "White": "#FFFFFF",
    "Black": "#000000", 
    "Blue": "#0066CC",
    "Red": "#CC0000",
    "Green": "#00CC66",
    "Gray": "#808080",
    "Navy": "#000080",
    "Cream": "#F5F5DC",
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
    """Remove background using rembg with better quality models"""
    # Convert to RGB if needed for better processing
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Save to bytes
    b = io.BytesIO()
    img.save(b, format="PNG", quality=95)
    
    # Use rembg with specified model for better quality - fix API usage
    try:
        from rembg import remove, new_session
        session = new_session(model_name)
        cut = remove(b.getvalue(), session=session)
    except:
        # Fallback to basic remove if session fails
        cut = remove(b.getvalue())
    
    result = Image.open(io.BytesIO(cut)).convert("RGBA")
    
    # Ensure high quality output
    return result

def remove_bg_only(img: Image.Image, model_quality: str = "Standard") -> Image.Image:
    """Remove background without cropping - just like remove.bg"""
    if img is None:
        return None
    
    # Map quality to rembg models
    model_map = {
        "Fast": "u2net",
        "Standard": "u2net", 
        "High Quality": "u2net_human_seg",
        "Portrait": "silueta"
    }
    
    model = model_map.get(model_quality, "u2net")
    return remove_bg(img, model)

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

def smart_background_removal(img: Image.Image, quality: str, crop_to_size: bool, size_label: str):
    """Smart background removal with quality control"""
    if img is None:
        return None
    
    if crop_to_size:
        target = PRESETS[size_label]
        cropped = smart_crop(img, target)
        return remove_bg_only(cropped, quality)
    else:
        return remove_bg_only(img, quality)

def solid_background(img: Image.Image, bg_color: str, size_label: str, crop_enabled: bool = True):
    """Add solid color background with optional cropping"""
    if img is None:
        return None
    
    if crop_enabled:
        target = PRESETS[size_label]
        cropped = smart_crop(img, target)
        fg = remove_bg(cropped)
        bg = Image.new("RGBA", target, bg_color)
        out = Image.alpha_composite(bg, fg).convert("RGB")
        return out
    else:
        # Use original image size
        fg = remove_bg(img)
        target = img.size
        bg = Image.new("RGBA", target, bg_color)
        out = Image.alpha_composite(bg, fg).convert("RGB")
        return out

def gradient_background(img: Image.Image, color1: str, color2: str, size_label: str, crop_enabled: bool = True):
    """Add gradient background with optional cropping"""
    if img is None:
        return None
    
    if crop_enabled:
        target = PRESETS[size_label]
        cropped = smart_crop(img, target)
        fg = remove_bg(cropped)
    else:
        target = img.size
        cropped = img
        fg = remove_bg(img)
    
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

# --- Enhanced UI with User Control ---
with gr.Blocks(title="PhotoFix - Professional Photo Editor", theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # 📸 PhotoFix - Professional Photo Editor
    **Choose exactly what you need - no automatic processing!**
    - 🎯 **Just Remove Background** - Like remove.bg
    - 🎨 **Custom Backgrounds** - Solid colors & gradients  
    - ✨ **Optional Enhancement** - Only when you want it
    - 👔 **Formal Attire** - Professional overlays
    """)
    
    with gr.Tab("🎯 Background Removal"):
        gr.Markdown("### Remove background without any automatic cropping - just like remove.bg!")
        
        with gr.Row():
            with gr.Column():
                bg_img = gr.Image(type="pil", label="📤 Upload Your Photo")
                
                with gr.Accordion("⚙️ Background Removal Settings", open=True):
                    bg_quality = gr.Dropdown(
                        choices=["Fast", "Standard", "High Quality", "Portrait"],
                        value="Standard",
                        label="🎯 Removal Quality"
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
                
                btn_remove_bg = gr.Button("🎯 Remove Background", variant="primary", size="lg")
            
            with gr.Column():
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
            # Social media: just remove background, keep original size
            return remove_bg_only(img, "Standard")
    
    # Event handlers
    def get_bg_color(preset_choice, custom_color):
        return BG_COLORS.get(preset_choice, custom_color)
    
    # Background removal
    btn_remove_bg.click(
        smart_background_removal,
        inputs=[bg_img, bg_quality, crop_bg, bg_size],
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
