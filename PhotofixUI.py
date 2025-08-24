import io, os
from dataclasses import dataclass
from typing import Tuple, Optional
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
import gradio as gr
from rembg import remove
import cv2
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
PHOTO_SIZES = {
    "1x1 inch": (300, 300),
    "2x2 inch": (600, 600), 
    "35x45mm": (413, 531),
    "Custom": (512, 512)
}

# Background colors
BG_COLORS = ["#FFFFFF", "#000000", "#0066CC", "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FECA57"]

@dataclass
class FaceBox:
    x: int; y: int; w: int; h: int

def detect_face_box(img: Image.Image) -> FaceBox | None:
    """Return first face box or None (uses MediaPipe if available)."""
    if not _HAVE_MP:
        return None
    try:
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
    except:
        return None

def smart_crop(img: Image.Image, target_size: Tuple[int,int]) -> Image.Image:
    """Smart crop for ID photos"""
    Wt, Ht = target_size
    ar_t = Wt / Ht
    
    fb = detect_face_box(img)
    if not fb:
        # Fallback to center crop
        W, H = img.size
        ar = W / H
        if ar > ar_t:
            newW = int(H * ar_t)
            x1 = (W - newW) // 2
            cropped = img.crop((x1, 0, x1 + newW, H))
        else:
            newH = int(W / ar_t)
            y1 = (H - newH) // 2
            cropped = img.crop((0, y1, W, y1 + newH))
        return cropped.resize((Wt, Ht), Image.LANCZOS)

    # Smart crop with face detection
    cx, cy = fb.x + fb.w/2, fb.y + fb.h/2
    head_h = fb.h * 1.2
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
        return img.resize((Wt, Ht), Image.LANCZOS)

    return img.crop((x1, y1, x2, y2)).resize((Wt, Ht), Image.LANCZOS)

def remove_background(img: Image.Image) -> Image.Image:
    """Remove background using rembg"""
    if img is None:
        return None
    
    # Convert to RGB if needed
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    try:
        # Save to bytes and process
        b = io.BytesIO()
        img.save(b, format="PNG")
        
        # Remove background
        cut = remove(b.getvalue())
        result = Image.open(io.BytesIO(cut)).convert("RGBA")
        return result
    except Exception as e:
        print(f"Background removal error: {e}")
        return img.convert("RGBA")

def change_background(img: Image.Image, bg_color: str) -> Image.Image:
    """Change background to solid color"""
    if img is None:
        return None
    
    # Remove background first
    fg = remove_background(img)
    
    # Create background
    bg = Image.new("RGBA", fg.size, bg_color)
    
    # Composite
    result = Image.alpha_composite(bg, fg).convert("RGB")
    return result

def add_formal_attire(img: Image.Image, style: str) -> Image.Image:
    """Add formal attire overlay"""
    if img is None:
        return None
    
    # For now, return original image
    # In a real implementation, you'd add suit overlays here
    return img

def enhance_picture(img: Image.Image, intensity: float = 0.3) -> Image.Image:
    """Enhance picture quality"""
    if img is None:
        return None
    
    try:
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
        enhanced = Image.fromarray(result_rgb)
        
        # Additional enhancement
        enhancer = ImageEnhance.Color(enhanced)
        enhanced = enhancer.enhance(1.1)
        
        enhancer = ImageEnhance.Contrast(enhanced)
        enhanced = enhancer.enhance(1.05)
        
        return enhanced
    except Exception as e:
        print(f"Enhancement error: {e}")
        return img

# Custom CSS for PhotoRoom-like styling
custom_css = """
.container {
    max-width: 1200px;
    margin: 0 auto;
}

.upload-area {
    border: 2px dashed #e1e5e9;
    border-radius: 12px;
    padding: 40px;
    text-align: center;
    background: #f8fafc;
    margin: 20px 0;
}

.tool-section {
    background: white;
    border-radius: 12px;
    padding: 24px;
    margin: 16px 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.tool-item {
    display: flex;
    align-items: center;
    padding: 16px;
    border-radius: 8px;
    margin: 8px 0;
    cursor: pointer;
    transition: background-color 0.2s;
}

.tool-item:hover {
    background-color: #f1f5f9;
}

.color-picker {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    border: 2px solid #e2e8f0;
    margin: 8px;
    cursor: pointer;
}

.formal-option {
    width: 120px;
    height: 160px;
    border-radius: 8px;
    margin: 8px;
    cursor: pointer;
    border: 2px solid transparent;
    transition: border-color 0.2s;
}

.formal-option:hover {
    border-color: #8b5cf6;
}

.export-section {
    background: white;
    border-radius: 12px;
    padding: 24px;
    margin: 16px 0;
}

.size-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin: 16px 0;
}

.size-option {
    background: #f8fafc;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
    cursor: pointer;
    border: 2px solid transparent;
    transition: all 0.2s;
}

.size-option:hover {
    border-color: #8b5cf6;
    background: #faf5ff;
}

.preview-area {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
    margin: 24px 0;
}

.preview-box {
    background: white;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
}

.download-btn {
    background: #8b5cf6;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px 24px;
    font-weight: 600;
    cursor: pointer;
    transition: background-color 0.2s;
    width: 100%;
    margin: 8px 0;
}

.download-btn:hover {
    background: #7c3aed;
}

.download-btn.secondary {
    background: #e2e8f0;
    color: #475569;
}

.download-btn.secondary:hover {
    background: #cbd5e1;
}
"""

# Main Gradio Interface
with gr.Blocks(title="PhotoFix - Professional ID Photo Editor", css=custom_css, theme=gr.themes.Soft()) as demo:
    
    # Header
    with gr.Row():
        gr.HTML("""
        <div style="display: flex; align-items: center; padding: 20px 0;">
            <div style="background: #8b5cf6; color: white; padding: 8px 12px; border-radius: 8px; margin-right: 12px; font-weight: bold;">
                📸 PhotoFix
            </div>
            <h2 style="margin: 0; color: #1e293b;">Professional ID Photo Editor</h2>
        </div>
        """)
    
    # Main content area with tabs
    with gr.Tab("Upload Photo"):
        with gr.Row():
            with gr.Column(scale=1):
                # Upload area
                input_image = gr.Image(
                    type="pil", 
                    label="📤 Upload Your Photo",
                    elem_classes="upload-area"
                )
                
            with gr.Column(scale=1):
                gr.HTML("""
                <div style="padding: 40px; text-align: center; color: #64748b;">
                    <h3>Edit & Enhance</h3>
                    <p>Upload your photo to start editing</p>
                </div>
                """)
    
    with gr.Tab("Edit & Enhance"):
        with gr.Row():
            with gr.Column(scale=1):
                # Editing Tools Section
                with gr.Group():
                    gr.HTML("""
                    <div class="tool-section">
                        <h3 style="margin-bottom: 20px; color: #1e293b;">Editing Tools</h3>
                    </div>
                    """)
                    
                    # Remove Background
                    with gr.Row():
                        gr.HTML("""
                        <div style="display: flex; align-items: center; padding: 16px;">
                            <span style="margin-right: 12px; font-size: 18px;">✂️</span>
                            <span style="font-weight: 500;">Remove Background</span>
                        </div>
                        """)
                        remove_bg_btn = gr.Button("Remove", variant="secondary", size="sm")
                    
                    # Change Background
                    with gr.Group():
                        gr.HTML("""
                        <div style="display: flex; align-items: center; padding: 16px 16px 8px 16px;">
                            <span style="margin-right: 12px; font-size: 18px;">🎨</span>
                            <span style="font-weight: 500;">Change Background</span>
                        </div>
                        """)
                        
                        # Color options
                        with gr.Row():
                            bg_color_1 = gr.Button("", variant="secondary", elem_classes="color-picker", 
                                                 elem_id="color-white", size="sm")
                            bg_color_2 = gr.Button("", variant="secondary", elem_classes="color-picker", 
                                                 elem_id="color-blue", size="sm")
                            bg_color_3 = gr.Button("", variant="secondary", elem_classes="color-picker", 
                                                 elem_id="color-red", size="sm")
                            custom_bg_color = gr.ColorPicker(value="#FFFFFF", label="Custom", scale=1)
                    
                    # Formal Attire
                    with gr.Group():
                        gr.HTML("""
                        <div style="display: flex; align-items: center; padding: 16px 16px 8px 16px;">
                            <span style="margin-right: 12px; font-size: 18px;">👔</span>
                            <span style="font-weight: 500;">Formal Attire</span>
                        </div>
                        """)
                        
                        with gr.Row():
                            formal_suit = gr.Button("Suit", variant="secondary", size="sm")
                            formal_shirt = gr.Button("Shirt", variant="secondary", size="sm")
                            formal_blazer = gr.Button("Blazer", variant="secondary", size="sm")
                    
                    # Enhance Picture
                    with gr.Row():
                        gr.HTML("""
                        <div style="display: flex; align-items: center; padding: 16px;">
                            <span style="margin-right: 12px; font-size: 18px;">✨</span>
                            <span style="font-weight: 500;">Enhance Picture</span>
                        </div>
                        """)
                        enhance_btn = gr.Button("Enhance", variant="secondary", size="sm")
                
                # Export Options
                with gr.Group():
                    gr.HTML("""
                    <div class="export-section">
                        <h3 style="margin-bottom: 20px; color: #1e293b;">Export Options</h3>
                    </div>
                    """)
                    
                    download_png_btn = gr.Button("📥 Download PNG", variant="primary", size="lg")
                    download_jpg_btn = gr.Button("📥 Download JPG", variant="secondary", size="lg")
                    
                    gr.HTML("""
                    <div style="margin: 20px 0;">
                        <h4 style="color: #64748b; margin-bottom: 16px;">ID Photo Sizes:</h4>
                    </div>
                    """)
                    
                    with gr.Row():
                        size_1x1 = gr.Button("1x1 inch", variant="secondary")
                        size_2x2 = gr.Button("2x2 inch", variant="secondary")
                    
                    with gr.Row():
                        size_35x45 = gr.Button("35x45mm", variant="secondary")
                        size_custom = gr.Button("Custom", variant="secondary")
            
            with gr.Column(scale=1):
                # Preview Area
                with gr.Group():
                    gr.HTML("""
                    <div style="margin-bottom: 20px;">
                        <h3 style="color: #1e293b;">Preview</h3>
                    </div>
                    """)
                    
                    with gr.Row():
                        with gr.Column():
                            gr.HTML("<h4 style='text-align: center; color: #64748b;'>Original</h4>")
                            original_preview = gr.Image(type="pil", label="", interactive=False, height=300)
                        
                        with gr.Column():
                            gr.HTML("<h4 style='text-align: center; color: #64748b;'>Enhanced</h4>")
                            enhanced_preview = gr.Image(type="pil", label="", interactive=False, height=300)
    
    # State variables
    current_image = gr.State()
    processed_image = gr.State()
    
    # Event handlers
    def update_previews(img):
        return img, img, img
    
    def process_remove_bg(img):
        if img is None:
            return img, img
        result = remove_background(img)
        return img, result
    
    def process_bg_color(img, color):
        if img is None:
            return img, img
        result = change_background(img, color)
        return img, result
    
    def process_enhance(img):
        if img is None:
            return img, img
        result = enhance_picture(img)
        return img, result
    
    def process_formal(img, style):
        if img is None:
            return img, img
        result = add_formal_attire(img, style)
        return img, result
    
    def resize_image(img, size_name):
        if img is None or size_name not in PHOTO_SIZES:
            return img
        target_size = PHOTO_SIZES[size_name]
        return smart_crop(img, target_size)
    
    # Connect events
    input_image.upload(update_previews, inputs=input_image, outputs=[original_preview, enhanced_preview, current_image])
    
    remove_bg_btn.click(process_remove_bg, inputs=current_image, outputs=[original_preview, enhanced_preview])
    
    bg_color_1.click(lambda img: process_bg_color(img, "#FFFFFF"), inputs=current_image, outputs=[original_preview, enhanced_preview])
    bg_color_2.click(lambda img: process_bg_color(img, "#0066CC"), inputs=current_image, outputs=[original_preview, enhanced_preview])
    bg_color_3.click(lambda img: process_bg_color(img, "#FF6B6B"), inputs=current_image, outputs=[original_preview, enhanced_preview])
    
    enhance_btn.click(process_enhance, inputs=current_image, outputs=[original_preview, enhanced_preview])
    
    formal_suit.click(lambda img: process_formal(img, "suit"), inputs=current_image, outputs=[original_preview, enhanced_preview])
    formal_shirt.click(lambda img: process_formal(img, "shirt"), inputs=current_image, outputs=[original_preview, enhanced_preview])
    formal_blazer.click(lambda img: process_formal(img, "blazer"), inputs=current_image, outputs=[original_preview, enhanced_preview])
    
    size_1x1.click(lambda img: resize_image(img, "1x1 inch"), inputs=enhanced_preview, outputs=enhanced_preview)
    size_2x2.click(lambda img: resize_image(img, "2x2 inch"), inputs=enhanced_preview, outputs=enhanced_preview)
    size_35x45.click(lambda img: resize_image(img, "35x45mm"), inputs=enhanced_preview, outputs=enhanced_preview)

if __name__ == "__main__":
    demo.launch(share=True, debug=False)
