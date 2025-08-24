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

# ---------- Configuration ----------
PHOTO_SIZES = {
    "1x1 inch": (300, 300),
    "2x2 inch": (600, 600), 
    "35x45mm": (413, 531),
    "Custom": (512, 512)
}

# Background colors matching the reference design
BACKGROUND_COLORS = [
    {"name": "White", "value": "#ffffff"},
    {"name": "Light Blue", "value": "#dbeafe"},
    {"name": "Light Gray", "value": "#f3f4f6"},
    {"name": "Red", "value": "#fecaca"}
]

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
    
    try:
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

def add_formal_attire(img: Image.Image, style: str) -> Image.Image:
    """Add formal attire overlay (placeholder for now)"""
    if img is None:
        return None
    # For now, return enhanced image
    return enhance_picture(img)

# Custom CSS to match the reference design exactly
custom_css = """
/* Main container styling */
.gradio-container {
    max-width: 1200px !important;
    margin: 0 auto !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* Header styling */
.header-container {
    background: #f1f5f9 !important;
    border-bottom: 1px solid #e5e7eb !important;
    padding: 16px 24px !important;
    margin-bottom: 32px !important;
}

.header-content {
    display: flex !important;
    align-items: center !important;
    gap: 12px !important;
}

.logo {
    width: 32px !important;
    height: 32px !important;
    background: #8b5cf6 !important;
    border-radius: 8px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    color: white !important;
    font-weight: bold !important;
}

.header-title {
    font-size: 24px !important;
    font-weight: bold !important;
    color: #1f2937 !important;
    margin: 0 !important;
}

.header-subtitle {
    font-size: 14px !important;
    color: #6b7280 !important;
}

/* Tab styling */
.tab-nav {
    background: #f9fafb !important;
    border-radius: 8px !important;
    padding: 4px !important;
    margin-bottom: 32px !important;
}

/* Upload area styling */
.upload-card {
    border: 2px dashed #d1d5db !important;
    border-radius: 12px !important;
    background: #f9fafb !important;
    padding: 48px 24px !important;
    text-align: center !important;
    transition: border-color 0.2s ease !important;
}

.upload-card:hover {
    border-color: #8b5cf6 !important;
}

.upload-icon {
    width: 64px !important;
    height: 64px !important;
    background: #f3f4f6 !important;
    border-radius: 50% !important;
    margin: 0 auto 16px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}

/* Tools section styling */
.tools-card {
    background: white !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 12px !important;
    padding: 24px !important;
    margin-bottom: 16px !important;
}

.tools-title {
    font-size: 18px !important;
    font-weight: 600 !important;
    color: #1f2937 !important;
    margin-bottom: 16px !important;
}

.tool-button {
    width: 100% !important;
    height: 48px !important;
    background: transparent !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 8px !important;
    padding: 12px 16px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    gap: 12px !important;
    margin-bottom: 8px !important;
    transition: all 0.2s ease !important;
}

.tool-button:hover {
    background: #f9fafb !important;
    border-color: #8b5cf6 !important;
}

/* Color picker styling */
.color-grid {
    display: grid !important;
    grid-template-columns: repeat(4, 1fr) !important;
    gap: 8px !important;
    padding: 0 16px !important;
    margin-top: 8px !important;
}

.color-button {
    width: 32px !important;
    height: 32px !important;
    border-radius: 50% !important;
    border: 2px solid #e5e7eb !important;
    cursor: pointer !important;
    transition: border-color 0.2s ease !important;
}

.color-button:hover {
    border-color: #8b5cf6 !important;
}

.color-button.selected {
    border-color: #8b5cf6 !important;
    border-width: 3px !important;
}

/* Attire options styling */
.attire-grid {
    display: grid !important;
    grid-template-columns: repeat(3, 1fr) !important;
    gap: 8px !important;
    padding: 0 16px !important;
    margin-top: 8px !important;
}

.attire-button {
    aspect-ratio: 1 !important;
    border: 2px solid #e5e7eb !important;
    border-radius: 8px !important;
    overflow: hidden !important;
    cursor: pointer !important;
    background: #f3f4f6 !important;
    transition: border-color 0.2s ease !important;
}

.attire-button:hover {
    border-color: #8b5cf6 !important;
}

/* Export section styling */
.export-card {
    background: white !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 12px !important;
    padding: 24px !important;
}

.primary-button {
    background: #8b5cf6 !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 12px 24px !important;
    font-weight: 600 !important;
    width: 100% !important;
    margin-bottom: 8px !important;
}

.secondary-button {
    background: transparent !important;
    color: #374151 !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 8px !important;
    padding: 12px 24px !important;
    font-weight: 600 !important;
    width: 100% !important;
    margin-bottom: 8px !important;
}

.size-grid {
    display: grid !important;
    grid-template-columns: 1fr 1fr !important;
    gap: 8px !important;
    margin-top: 8px !important;
}

.size-button {
    background: transparent !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 6px !important;
    padding: 8px 12px !important;
    font-size: 14px !important;
    cursor: pointer !important;
}

/* Preview cards styling */
.preview-grid {
    display: grid !important;
    grid-template-columns: 1fr 1fr !important;
    gap: 16px !important;
}

.preview-card {
    background: white !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 12px !important;
    padding: 20px !important;
}

.preview-title {
    font-size: 16px !important;
    font-weight: 500 !important;
    color: #374151 !important;
    margin-bottom: 12px !important;
    text-align: center !important;
}

.preview-image {
    aspect-ratio: 3/4 !important;
    background: #f3f4f6 !important;
    border-radius: 8px !important;
    overflow: hidden !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}

.preview-placeholder {
    text-align: center !important;
    color: #6b7280 !important;
}

/* Progress bar styling */
.progress-container {
    background: white !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 12px !important;
    padding: 24px !important;
    margin-bottom: 16px !important;
}

.progress-text {
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
    margin-bottom: 12px !important;
    font-weight: 500 !important;
    color: #374151 !important;
}

.spinner {
    width: 16px !important;
    height: 16px !important;
    border: 2px solid #8b5cf6 !important;
    border-top: 2px solid transparent !important;
    border-radius: 50% !important;
    animation: spin 1s linear infinite !important;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}
"""

# Main Gradio Interface with exact design copy
with gr.Blocks(title="PhotoFix - Professional ID Photo Editor", css=custom_css, theme=gr.themes.Soft()) as demo:
    
    # Header exactly like the reference
    gr.HTML("""
    <div class="header-container">
        <div class="header-content">
            <div class="logo">📸</div>
            <h1 class="header-title">PhotoFix</h1>
            <span class="header-subtitle">Professional ID Photo Editor</span>
        </div>
    </div>
    """)
    
    # State variables
    uploaded_image = gr.State()
    processed_image = gr.State()
    selected_background = gr.State("#ffffff")
    selected_attire = gr.State("")
    is_processing = gr.State(False)
    
    # Tab interface exactly like reference
    with gr.Tabs(elem_classes="tab-nav") as tabs:
        
        # Upload Photo Tab
        with gr.Tab("Upload Photo", id="upload"):
            with gr.Row():
                with gr.Column(scale=1):
                    # Upload area with exact styling
                    gr.HTML("""
                    <div class="upload-card">
                        <div class="upload-icon">
                            <span style="font-size: 32px; color: #6b7280;">📤</span>
                        </div>
                        <h3 style="font-size: 18px; font-weight: 600; color: #1f2937; margin-bottom: 8px;">Upload Your Photo</h3>
                        <p style="color: #6b7280; margin-bottom: 16px;">Drag and drop your image here, or click to browse</p>
                        <p style="font-size: 14px; color: #9ca3af;">Supports JPG, PNG files up to 10MB</p>
                    </div>
                    """)
                    
                    input_image = gr.Image(
                        type="pil", 
                        label="",
                        elem_classes="upload-area",
                        height=300
                    )
                    
                with gr.Column(scale=1):
                    gr.HTML("""
                    <div style="padding: 80px 40px; text-align: center;">
                        <h3 style="color: #374151; margin-bottom: 16px;">Edit & Enhance</h3>
                        <p style="color: #6b7280;">Upload your photo to start editing</p>
                    </div>
                    """)
        
        # Edit & Enhance Tab
        with gr.Tab("Edit & Enhance", id="edit"):
            with gr.Row():
                # Tools Sidebar (exact copy of reference)
                with gr.Column(scale=1):
                    
                    # Editing Tools Card
                    with gr.Group():
                        gr.HTML("""
                        <div class="tools-card">
                            <h3 class="tools-title">Editing Tools</h3>
                        </div>
                        """)
                        
                        # Remove Background Tool
                        remove_bg_btn = gr.Button(
                            "✂️ Remove Background", 
                            elem_classes="tool-button",
                            variant="secondary"
                        )
                        
                        # Change Background Tool
                        change_bg_btn = gr.Button(
                            "🎨 Change Background", 
                            elem_classes="tool-button",
                            variant="secondary"
                        )
                        
                        # Background Color Options
                        gr.HTML("""
                        <div class="color-grid">
                            <div class="color-button" style="background-color: #ffffff;" onclick="selectColor('#ffffff')" title="White"></div>
                            <div class="color-button" style="background-color: #dbeafe;" onclick="selectColor('#dbeafe')" title="Light Blue"></div>
                            <div class="color-button" style="background-color: #f3f4f6;" onclick="selectColor('#f3f4f6')" title="Light Gray"></div>
                            <div class="color-button" style="background-color: #fecaca;" onclick="selectColor('#fecaca')" title="Red"></div>
                        </div>
                        """)
                        
                        # Formal Attire Tool
                        formal_attire_btn = gr.Button(
                            "👔 Formal Attire", 
                            elem_classes="tool-button",
                            variant="secondary"
                        )
                        
                        # Attire Options
                        with gr.Row():
                            navy_blazer_btn = gr.Button("Navy", size="sm", variant="secondary")
                            white_shirt_btn = gr.Button("Shirt", size="sm", variant="secondary")
                            black_suit_btn = gr.Button("Suit", size="sm", variant="secondary")
                        
                        # Enhance Picture Tool
                        enhance_btn = gr.Button(
                            "✨ Enhance Picture", 
                            elem_classes="tool-button",
                            variant="secondary"
                        )
                    
                    # Export Options Card
                    with gr.Group():
                        gr.HTML("""
                        <div class="export-card">
                            <h3 class="tools-title">Export Options</h3>
                        </div>
                        """)
                        
                        download_png_btn = gr.Button(
                            "📥 Download PNG", 
                            elem_classes="primary-button",
                            variant="primary"
                        )
                        
                        download_jpg_btn = gr.Button(
                            "📥 Download JPG", 
                            elem_classes="secondary-button",
                            variant="secondary"
                        )
                        
                        gr.HTML("""
                        <div style="padding-top: 16px; border-top: 1px solid #e5e7eb; margin-top: 16px;">
                            <p style="font-size: 14px; color: #6b7280; margin-bottom: 8px;">ID Photo Sizes:</p>
                        </div>
                        """)
                        
                        with gr.Row():
                            size_1x1_btn = gr.Button("1x1 inch", size="sm", variant="secondary")
                            size_2x2_btn = gr.Button("2x2 inch", size="sm", variant="secondary")
                        
                        with gr.Row():
                            size_35x45_btn = gr.Button("35x45mm", size="sm", variant="secondary")
                            size_custom_btn = gr.Button("Custom", size="sm", variant="secondary")
                
                # Image Preview Area (exact copy of reference)
                with gr.Column(scale=2):
                    
                    # Progress indicator (hidden by default)
                    progress_indicator = gr.HTML(visible=False)
                    
                    # Preview Grid
                    with gr.Row():
                        # Original Image Preview
                        with gr.Column():
                            gr.HTML("""
                            <div class="preview-card">
                                <h4 class="preview-title">Original</h4>
                            </div>
                            """)
                            original_preview = gr.Image(
                                type="pil", 
                                label="",
                                interactive=False,
                                height=400,
                                elem_classes="preview-image"
                            )
                        
                        # Enhanced Image Preview
                        with gr.Column():
                            gr.HTML("""
                            <div class="preview-card">
                                <h4 class="preview-title">Enhanced ✓</h4>
                            </div>
                            """)
                            enhanced_preview = gr.Image(
                                type="pil", 
                                label="",
                                interactive=False,
                                height=400,
                                elem_classes="preview-image"
                            )
    
    # Event handlers with progress simulation
    def show_progress(action_name):
        return gr.update(
            visible=True,
            value=f"""
            <div class="progress-container">
                <div class="progress-text">
                    <div class="spinner"></div>
                    <span>Processing your image...</span>
                </div>
                <div style="background: #f3f4f6; height: 8px; border-radius: 4px; overflow: hidden;">
                    <div style="background: #8b5cf6; height: 100%; width: 60%; border-radius: 4px; animation: progress-fill 2s ease-in-out;"></div>
                </div>
            </div>
            <style>
                @keyframes progress-fill {{
                    from {{ width: 0%; }}
                    to {{ width: 100%; }}
                }}
            </style>
            """
        )
    
    def hide_progress():
        return gr.update(visible=False)
    
    def update_previews(img):
        if img is None:
            return None, None, img, None
        return img, img, img, img
    
    def process_remove_bg(img):
        if img is None:
            return img, img, show_progress("remove-background")
        result = remove_background(img)
        return img, result, hide_progress()
    
    def process_bg_color(img, color="#ffffff"):
        if img is None:
            return img, img, show_progress("change-background")
        result = change_background(img, color)
        return img, result, hide_progress()
    
    def process_enhance(img):
        if img is None:
            return img, img, show_progress("enhance")
        result = enhance_picture(img)
        return img, result, hide_progress()
    
    def process_formal(img, style):
        if img is None:
            return img, img, show_progress("formal-attire")
        result = add_formal_attire(img, style)
        return img, result, hide_progress()
    
    def resize_image(img, size_name):
        if img is None or size_name not in PHOTO_SIZES:
            return img
        target_size = PHOTO_SIZES[size_name]
        return smart_crop(img, target_size)
    
    # Connect events exactly like the reference
    input_image.upload(
        update_previews, 
        inputs=input_image, 
        outputs=[original_preview, enhanced_preview, uploaded_image, processed_image]
    )
    
    remove_bg_btn.click(
        process_remove_bg, 
        inputs=uploaded_image, 
        outputs=[original_preview, enhanced_preview, progress_indicator]
    )
    
    change_bg_btn.click(
        lambda img: process_bg_color(img, "#ffffff"), 
        inputs=uploaded_image, 
        outputs=[original_preview, enhanced_preview, progress_indicator]
    )
    
    enhance_btn.click(
        process_enhance, 
        inputs=uploaded_image, 
        outputs=[original_preview, enhanced_preview, progress_indicator]
    )
    
    navy_blazer_btn.click(
        lambda img: process_formal(img, "navy"), 
        inputs=uploaded_image, 
        outputs=[original_preview, enhanced_preview, progress_indicator]
    )
    
    white_shirt_btn.click(
        lambda img: process_formal(img, "shirt"), 
        inputs=uploaded_image, 
        outputs=[original_preview, enhanced_preview, progress_indicator]
    )
    
    black_suit_btn.click(
        lambda img: process_formal(img, "suit"), 
        inputs=uploaded_image, 
        outputs=[original_preview, enhanced_preview, progress_indicator]
    )
    
    # Size buttons
    size_1x1_btn.click(
        lambda img: resize_image(img, "1x1 inch"), 
        inputs=enhanced_preview, 
        outputs=enhanced_preview
    )
    
    size_2x2_btn.click(
        lambda img: resize_image(img, "2x2 inch"), 
        inputs=enhanced_preview, 
        outputs=enhanced_preview
    )
    
    size_35x45_btn.click(
        lambda img: resize_image(img, "35x45mm"), 
        inputs=enhanced_preview, 
        outputs=enhanced_preview
    )

if __name__ == "__main__":
    demo.launch(share=True, debug=False)
