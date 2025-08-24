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

# ---------- ID size presets ----------
PRESETS = {
    "Original Size": None,  # Keep original size
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

def simple_remove_bg(img: Image.Image) -> Image.Image:
    """Simple background removal like remove.bg"""
    if img is None:
        return None
    
    # Convert to RGB if needed
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Save to bytes and process
    b = io.BytesIO()
    img.save(b, format="PNG")
    
    # Remove background
    cut = remove(b.getvalue())
    result = Image.open(io.BytesIO(cut)).convert("RGBA")
    
    return result

def add_solid_background(img: Image.Image, bg_color: str) -> Image.Image:
    """Add solid background to image"""
    if img is None:
        return None
    
    # Remove background first
    fg = simple_remove_bg(img)
    
    # Create background
    bg = Image.new("RGBA", fg.size, bg_color)
    
    # Composite
    result = Image.alpha_composite(bg, fg).convert("RGB")
    return result

def crop_image(img: Image.Image, size_preset: str) -> Image.Image:
    """Crop image to specified size"""
    if img is None or size_preset == "Original Size":
        return img
    
    target_size = PRESETS[size_preset]
    if target_size is None:
        return img
    
    return smart_crop(img, target_size)

def remove_blemishes_simple(img: Image.Image, intensity: float = 0.3) -> Image.Image:
    """Simple blemish removal"""
    if img is None:
        return None
    
    # Convert PIL to OpenCV
    img_array = np.array(img)
    if len(img_array.shape) == 4:  # RGBA
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
    elif len(img_array.shape) == 3:  # RGB
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    # Apply bilateral filter for smoothing
    smooth = cv2.bilateralFilter(img_array, 15, 80, 80)
    
    # Blend with original
    result = cv2.addWeighted(img_array, 1-intensity, smooth, intensity, 0)
    
    # Convert back to PIL
    result_rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
    return Image.fromarray(result_rgb)

# Simple UI
with gr.Blocks(title="PhotoFix - Simple Photo Editor", theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # 📸 PhotoFix - Simple Photo Editor
    **Easy photo editing with user control:**
    - 🎯 Remove Background (like remove.bg)
    - 🎨 Add Background Colors
    - ✨ Remove Blemishes
    - 📐 Optional Cropping
    """)
    
    with gr.Tab("🎯 Background Removal"):
        with gr.Row():
            with gr.Column():
                bg_input = gr.Image(type="pil", label="📤 Upload Photo")
                crop_checkbox = gr.Checkbox(label="📐 Crop to specific size", value=False)
                size_dropdown = gr.Dropdown(
                    choices=list(PRESETS.keys()),
                    value="Original Size",
                    label="Photo Size",
                    visible=False
                )
                remove_btn = gr.Button("🎯 Remove Background", variant="primary")
            
            with gr.Column():
                bg_output = gr.Image(type="pil", label="✨ Result")
        
        # Show/hide size dropdown
        crop_checkbox.change(
            lambda x: gr.update(visible=x),
            inputs=crop_checkbox,
            outputs=size_dropdown
        )
    
    with gr.Tab("🎨 Add Background"):
        with gr.Row():
            with gr.Column():
                color_input = gr.Image(type="pil", label="📤 Upload Photo")
                bg_color_dropdown = gr.Dropdown(
                    choices=list(BG_COLORS.keys()),
                    value="White",
                    label="Background Color"
                )
                custom_color = gr.ColorPicker(value="#FFFFFF", label="Custom Color")
                crop_bg_checkbox = gr.Checkbox(label="📐 Crop to specific size", value=False)
                size_bg_dropdown = gr.Dropdown(
                    choices=list(PRESETS.keys()),
                    value="Original Size",
                    label="Photo Size",
                    visible=False
                )
                color_btn = gr.Button("🎨 Add Background", variant="primary")
            
            with gr.Column():
                color_output = gr.Image(type="pil", label="🎨 Result")
        
        crop_bg_checkbox.change(
            lambda x: gr.update(visible=x),
            inputs=crop_bg_checkbox,
            outputs=size_bg_dropdown
        )
    
    with gr.Tab("✨ Enhancement"):
        with gr.Row():
            with gr.Column():
                enhance_input = gr.Image(type="pil", label="📤 Upload Photo")
                blemish_intensity = gr.Slider(
                    minimum=0.0, maximum=1.0, value=0.3,
                    label="Blemish Removal Intensity"
                )
                crop_enhance_checkbox = gr.Checkbox(label="📐 Crop to specific size", value=False)
                size_enhance_dropdown = gr.Dropdown(
                    choices=list(PRESETS.keys()),
                    value="Original Size",
                    label="Photo Size",
                    visible=False
                )
                enhance_btn = gr.Button("✨ Enhance", variant="primary")
            
            with gr.Column():
                enhance_output = gr.Image(type="pil", label="✨ Enhanced")
        
        crop_enhance_checkbox.change(
            lambda x: gr.update(visible=x),
            inputs=crop_enhance_checkbox,
            outputs=size_enhance_dropdown
        )
    
    # Event handlers
    def process_bg_removal(img, crop_enabled, size_preset):
        if img is None:
            return None
        
        if crop_enabled and size_preset != "Original Size":
            img = crop_image(img, size_preset)
        
        return simple_remove_bg(img)
    
    def process_bg_color(img, color_preset, custom_color_val, crop_enabled, size_preset):
        if img is None:
            return None
        
        if crop_enabled and size_preset != "Original Size":
            img = crop_image(img, size_preset)
        
        # Get color
        bg_color = BG_COLORS.get(color_preset, custom_color_val)
        return add_solid_background(img, bg_color)
    
    def process_enhancement(img, intensity, crop_enabled, size_preset):
        if img is None:
            return None
        
        if crop_enabled and size_preset != "Original Size":
            img = crop_image(img, size_preset)
        
        return remove_blemishes_simple(img, intensity)
    
    # Connect buttons
    remove_btn.click(
        process_bg_removal,
        inputs=[bg_input, crop_checkbox, size_dropdown],
        outputs=bg_output
    )
    
    color_btn.click(
        process_bg_color,
        inputs=[color_input, bg_color_dropdown, custom_color, crop_bg_checkbox, size_bg_dropdown],
        outputs=color_output
    )
    
    enhance_btn.click(
        process_enhancement,
        inputs=[enhance_input, blemish_intensity, crop_enhance_checkbox, size_enhance_dropdown],
        outputs=enhance_output
    )

if __name__ == "__main__":
    demo.launch(share=True, debug=False)
