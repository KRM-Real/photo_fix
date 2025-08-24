"""
PhotoFix - Professional Photo Editor
Clean, modern UI with white background and dark fonts
"""

import gradio as gr
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import cv2
from rembg import remove, new_session
import mediapipe as mp
from skimage import morphology
import warnings
import os
import io
import base64
import requests
from templates import (
    get_header_html, 
    get_section_header, 
    get_upload_instructions,
    get_quick_tips,
    get_coming_soon,
    get_success_message,
    get_error_message
)

# Try to import Replicate
try:
    import replicate
    REPLICATE_AVAILABLE = True
except ImportError:
    REPLICATE_AVAILABLE = False

warnings.filterwarnings("ignore")

def load_css():
    """Load CSS from external file"""
    try:
        with open('styles.css', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print("Warning: styles.css not found, using minimal inline styles")
        return """
        body, .main, .app { background: #ffffff !important; color: #1f2937 !important; }
        .gradio-container { max-width: 1400px !important; margin: 0 auto !important; }
        """

# Initialize MediaPipe
mp_face_detection = mp.solutions.face_detection

# Enhanced background removal models
QUALITY_MODELS = {
    "Fast": "u2net",
    "Standard": "u2netp", 
    "High Quality": "u2net_human_seg",
    "Portrait": "silueta",
    "Product": "isnet-general-use"
}

# Add Replicate option if available
if REPLICATE_AVAILABLE:
    QUALITY_MODELS["Replicate (Best Quality)"] = "replicate"

# Background color presets
BG_COLORS = {
    "Pure White": (255, 255, 255),
    "Soft Gray": (248, 249, 250),
    "Professional Blue": (37, 99, 235),
    "LinkedIn Blue": (0, 119, 181),
    "Passport Blue": (0, 82, 147),
    "Corporate Navy": (30, 58, 138),
    "Elegant Black": (17, 24, 39),
    "Warm Beige": (245, 240, 230),
    "Studio Gray": (156, 163, 175)
}

# Size presets for common requirements
PRESETS = {
    "Keep Original Size": None,
    "2x2 in @300DPI (600x600)": (600, 600),
    "1.5x2 in @300DPI (450x600)": (450, 600),
    "35x45mm @300DPI (413x531)": (413, 531),
    "LinkedIn Profile (400x400)": (400, 400),
    "Square Instagram (1080x1080)": (1080, 1080),
    "Standard Portrait (600x800)": (600, 800),
    "ID Photo (300x400)": (300, 400),
    "Passport US (2x2 in)": (600, 600),
    "Custom Size": "custom"
}

def smart_face_crop(image, target_size, face_margin=0.3):
    """Smart crop focusing on detected face"""
    try:
        image_rgb = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        with mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.7) as face_detection:
            results = face_detection.process(cv2.cvtColor(image_rgb, cv2.COLOR_BGR2RGB))
            
            if results.detections:
                detection = results.detections[0]
                bbox = detection.location_data.relative_bounding_box
                
                h, w = image_rgb.shape[:2]
                face_x = int(bbox.xmin * w)
                face_y = int(bbox.ymin * h)
                face_w = int(bbox.width * w)
                face_h = int(bbox.height * h)
                
                margin_x = int(face_w * face_margin)
                margin_y = int(face_h * face_margin)
                
                crop_x1 = max(0, face_x - margin_x)
                crop_y1 = max(0, face_y - margin_y)
                crop_x2 = min(w, face_x + face_w + margin_x)
                crop_y2 = min(h, face_y + face_h + margin_y)
                
                cropped = image.crop((crop_x1, crop_y1, crop_x2, crop_y2))
                return cropped.resize(target_size, Image.Resampling.LANCZOS)
    except Exception as e:
        print(f"Face detection failed: {e}")
    
    return image.resize(target_size, Image.Resampling.LANCZOS)

def enhance_edges(mask):
    """Enhance mask edges for smoother cutouts"""
    try:
        mask_array = np.array(mask)
        
        # Remove small noise
        mask_array = morphology.remove_small_objects(mask_array > 128, min_size=100)
        mask_array = morphology.remove_small_holes(mask_array, area_threshold=100)
        
        # Smooth edges
        mask_array = mask_array.astype(np.uint8) * 255
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask_array = cv2.morphologyEx(mask_array, cv2.MORPH_CLOSE, kernel)
        mask_array = cv2.GaussianBlur(mask_array, (3, 3), 0)
        
        return Image.fromarray(mask_array)
    except Exception as e:
        print(f"Edge enhancement failed: {e}")
        return mask

def remove_bg_replicate(image, api_token=None):
    """Remove background using Replicate API"""
    try:
        # Set API token if provided
        if api_token:
            os.environ["REPLICATE_API_TOKEN"] = api_token
        
        # Check if API token is set
        if not os.environ.get("REPLICATE_API_TOKEN"):
            raise Exception("Replicate API token is required. Get one free at https://replicate.com")
        
        # Convert PIL image to base64
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # Create data URI
        data_uri = f"data:image/png;base64,{img_str}"
        
        # Call Replicate API
        output = replicate.run(
            "cjwbw/rembg:fb8af171cfa1616ddcf1242c093f9c46bcada5ad4cf6f2fbe8b81b330ec5c003",
            input={"image": data_uri}
        )
        
        # Download the result
        response = requests.get(output)
        result_image = Image.open(io.BytesIO(response.content))
        
        return result_image
    except Exception as e:
        print(f"Replicate background removal failed: {e}")
        raise e

def remove_bg_enhanced(image, quality="Standard", enhance_edges_flag=True, api_token=None):
    """Enhanced background removal with multiple models including Replicate"""
    try:
        if quality == "Replicate (Best Quality)" and REPLICATE_AVAILABLE:
            # Use Replicate API
            result = remove_bg_replicate(image, api_token)
            
            if enhance_edges_flag and result.mode == 'RGBA':
                # Extract and enhance the alpha channel
                alpha = result.split()[-1]
                enhanced_alpha = enhance_edges(alpha)
                
                # Recombine with enhanced alpha
                rgb = result.convert('RGB')
                result = Image.merge('RGBA', (*rgb.split(), enhanced_alpha))
            
            return result
        else:
            # Use local rembg
            model_name = QUALITY_MODELS.get(quality, "u2netp")
            session = new_session(model_name)
            
            # Remove background
            result = remove(image, session=session)
            
            if enhance_edges_flag and result.mode == 'RGBA':
                # Extract and enhance the alpha channel
                alpha = result.split()[-1]
                enhanced_alpha = enhance_edges(alpha)
                
                # Recombine with enhanced alpha
                rgb = result.convert('RGB')
                result = Image.merge('RGBA', (*rgb.split(), enhanced_alpha))
            
            return result
    except Exception as e:
        print(f"Background removal failed: {e}")
        raise e

def process_remove_background(image, quality, enhance_edges_flag, crop_enabled, crop_size, custom_width, custom_height, api_token=None):
    """Process background removal with all options"""
    if image is None:
        return None, "Please upload an image first!"
    
    try:
        # Remove background
        result = remove_bg_enhanced(image, quality, enhance_edges_flag, api_token)
        
        # Handle cropping
        if crop_enabled:
            if crop_size == "Custom Size":
                if custom_width and custom_height and custom_width > 0 and custom_height > 0:
                    target_size = (int(custom_width), int(custom_height))
                else:
                    return None, "Please enter valid custom dimensions!"
            else:
                target_size = PRESETS.get(crop_size)
                
            if target_size:
                result = smart_face_crop(result, target_size)
        
        return result, f"✅ Background removed successfully using {quality} quality!"
        
    except Exception as e:
        return None, f"❌ Error: {str(e)}"

def change_background_color(image, color_name):
    """Change background to solid color"""
    if image is None:
        return None, "Please upload an image first!"
    
    try:
        # Ensure image has transparency
        if image.mode != 'RGBA':
            image = remove_bg_enhanced(image)
        
        color = BG_COLORS.get(color_name, (255, 255, 255))
        
        # Create new background
        background = Image.new('RGB', image.size, color)
        
        # Composite the image onto the background
        if image.mode == 'RGBA':
            background.paste(image, mask=image.split()[-1])
        else:
            background.paste(image)
        
        return background, f"✅ Background changed to {color_name}!"
        
    except Exception as e:
        return None, f"❌ Error: {str(e)}"

# Modern, clean CSS
custom_css = """
/* Base styles */
* {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif !important;
}

/* Main container */
.gradio-container {
    max-width: 1400px !important;
    margin: 0 auto !important;
    background: #ffffff !important;
}

/* Header with gradient */
.header-modern {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: white !important;
    padding: 2rem !important;
    margin: -2rem -2rem 2rem -2rem !important;
    border-radius: 0 0 1rem 1rem !important;
    text-align: center !important;
}

.header-title {
    font-size: 2.5rem !important;
    font-weight: 800 !important;
    margin: 0 0 0.5rem 0 !important;
}

.header-subtitle {
    font-size: 1.1rem !important;
    opacity: 0.9 !important;
    margin: 0 !important;
}

/* Content cards */
.content-card {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 1rem !important;
    padding: 1.5rem !important;
    margin: 1rem 0 !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1) !important;
}

/* Buttons */
.btn-primary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    border: none !important;
    color: white !important;
    border-radius: 0.5rem !important;
    padding: 0.75rem 1.5rem !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
}

.btn-primary:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4) !important;
}

/* Form controls */
.form-control {
    border: 1px solid #d1d5db !important;
    border-radius: 0.5rem !important;
    background: #ffffff !important;
    color: #1f2937 !important;
}

/* Upload areas */
.upload-zone {
    background: #f8fafc !important;
    border: 2px dashed #cbd5e1 !important;
    border-radius: 1rem !important;
    padding: 2rem !important;
    text-align: center !important;
    transition: all 0.3s ease !important;
}

.upload-zone:hover {
    border-color: #667eea !important;
    background: #f0f4ff !important;
}

/* Text and labels */
label {
    color: #374151 !important;
    font-weight: 600 !important;
}

/* Ensure visibility */
body, .main, .app {
    background: #ffffff !important;
    color: #1f2937 !important;
}
"""

# Load CSS
custom_css = load_css()

# Add web-optimized CSS
web_css = """
<style>
/* Web-optimized styles */
.gradio-container {
    overflow-x: hidden !important;
    max-width: 1200px !important;
}

/* Prevent horizontal scroll */
body {
    overflow-x: hidden !important;
}

/* Web-optimized images */
.gr-image img {
    width: 100% !important;
    height: auto !important;
    object-fit: contain !important;
    max-height: 600px !important;
}

/* Compact upload areas for web */
.gr-file-upload {
    padding: 1.5rem !important;
    min-height: 200px !important;
}

/* Better web layout */
.gr-row {
    gap: 2rem !important;
}

.gr-column {
    flex: 1 !important;
}

/* Web-optimized buttons */
.gr-button {
    padding: 0.75rem 2rem !important;
    border-radius: 0.5rem !important;
}
</style>
"""

# Create the interface with clean white background and dark fonts
with gr.Blocks(
    title="PhotoFix - Professional Photo Editor", 
    css=custom_css + web_css, 
    theme=gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="gray",
        neutral_hue="gray"
    )
) as demo:
    
    # Header optimized for web view
    gr.HTML(get_header_html())
    
    # Quick tips section
    gr.HTML(get_quick_tips())
    
    with gr.Tabs():
        # Background Removal Tab
        with gr.Tab("🎯 Background Removal"):
            gr.HTML(get_section_header(
                "🎯 Remove Background", 
                "Remove background like remove.bg with professional quality!"
            ))
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.HTML(get_upload_instructions())
                    bg_input = gr.Image(
                        type="pil", 
                        label="Upload Your Photo",
                        elem_classes="upload-area"
                    )
                    
                    with gr.Group(elem_classes="content-section"):
                        gr.Markdown("### ⚙️ Settings")
                        
                        bg_quality = gr.Dropdown(
                            choices=list(QUALITY_MODELS.keys()),
                            value="Replicate (Best Quality)" if REPLICATE_AVAILABLE else "Standard",
                            label="🎯 Removal Quality",
                            info="Replicate: Best quality (cloud-based) | Standard: Good for people | Product: Best for objects"
                        )
                        
                        # Replicate API key input (only show if Replicate is available)
                        if REPLICATE_AVAILABLE:
                            replicate_api_key = gr.Textbox(
                                label="🔑 Replicate API Token (Optional)",
                                type="password",
                                placeholder="Get your free token from replicate.com",
                                info="Required only for Replicate option. Get free token at https://replicate.com"
                            )
                        else:
                            replicate_api_key = gr.Textbox(visible=False)
                        
                        enhance_edges_checkbox = gr.Checkbox(
                            value=True,
                            label="✨ Enhance edges for smoother cutouts",
                            info="Applies post-processing for cleaner edges"
                        )
                        
                        crop_enabled = gr.Checkbox(
                            value=False,
                            label="📐 Crop to specific size",
                            info="Enable to crop the result to standard sizes"
                        )
                        
                        crop_size = gr.Dropdown(
                            choices=list(PRESETS.keys()),
                            value="2x2 in @300DPI (600x600)",
                            label="📏 Crop Size",
                            visible=False,
                            info="Choose from common photo sizes"
                        )
                        
                        with gr.Row(visible=False) as custom_size_row:
                            custom_width = gr.Number(
                                label="Width (px)", 
                                value=600,
                                minimum=100,
                                maximum=4000
                            )
                            custom_height = gr.Number(
                                label="Height (px)", 
                                value=600,
                                minimum=100,
                                maximum=4000
                            )
                    
                    remove_bg_btn = gr.Button(
                        "🎯 Remove Background", 
                        variant="primary", 
                        elem_classes="btn-primary",
                        size="lg"
                    )
                    
                    bg_status = gr.Textbox(
                        label="Status", 
                        interactive=False,
                        elem_classes="form-control"
                    )
                
                with gr.Column(scale=1):
                    bg_output = gr.Image(
                        type="pil", 
                        label="✨ Result",
                        elem_classes="image-container"
                    )
        
        # Background Color Tab  
        with gr.Tab("🎨 Background Colors"):
            gr.HTML(get_section_header(
                "🎨 Change Background Color",
                "Add professional solid color backgrounds!"
            ))
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.HTML(get_upload_instructions())
                    color_input = gr.Image(
                        type="pil", 
                        label="Upload Your Photo",
                        elem_classes="upload-area"
                    )
                    
                    with gr.Group(elem_classes="content-section"):
                        gr.Markdown("### 🎨 Color Options")
                        
                        bg_color = gr.Dropdown(
                            choices=list(BG_COLORS.keys()),
                            value="Pure White",
                            label="Background Color",
                            info="Choose from professional color presets"
                        )
                    
                    change_color_btn = gr.Button(
                        "🎨 Change Background", 
                        variant="primary", 
                        elem_classes="btn-primary",
                        size="lg"
                    )
                    
                    color_status = gr.Textbox(
                        label="Status", 
                        interactive=False,
                        elem_classes="form-control"
                    )
                
                with gr.Column(scale=1):
                    color_output = gr.Image(
                        type="pil", 
                        label="✨ Result",
                        elem_classes="image-container"
                    )
        
        # Enhancement Tab (coming soon)
        with gr.Tab("✨ Enhancements"):
            gr.HTML(get_coming_soon())
    
    # Event handlers
    def toggle_crop_options(enabled):
        return gr.update(visible=enabled)
    
    def toggle_custom_size(size):
        return gr.update(visible=(size == "Custom Size"))
    
    crop_enabled.change(toggle_crop_options, crop_enabled, crop_size)
    crop_size.change(toggle_custom_size, crop_size, custom_size_row)
    
    # Button click handlers
    remove_bg_btn.click(
        process_remove_background,
        inputs=[bg_input, bg_quality, enhance_edges_checkbox, crop_enabled, crop_size, custom_width, custom_height, replicate_api_key],
        outputs=[bg_output, bg_status]
    )
    
    change_color_btn.click(
        change_background_color,
        inputs=[color_input, bg_color],
        outputs=[color_output, color_status]
    )

if __name__ == "__main__":
    demo.launch(
        share=False, 
        server_name="127.0.0.1", 
        server_port=7861,
        show_error=True,
        quiet=False
    )
