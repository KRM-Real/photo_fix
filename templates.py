"""
HTML templates for PhotoFix application
"""

def get_header_html():
    """Returns the main header HTML optimized for web view"""
    return """
    <div class="header-modern">
        <h1 class="header-title">📸 PhotoFix</h1>
        <p class="header-subtitle">Professional Photo Editor with AI-Powered Tools</p>
        <div class="feature-grid">
            <div class="feature-card">
                <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">🎯</div>
                <div style="font-weight: 700; font-size: 0.95rem; margin-bottom: 0.25rem;">Background Removal</div>
                <div style="font-size: 0.8rem; opacity: 0.9;">Like remove.bg quality</div>
            </div>
            <div class="feature-card">
                <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">🎨</div>
                <div style="font-weight: 700; font-size: 0.95rem; margin-bottom: 0.25rem;">Custom Backgrounds</div>
                <div style="font-size: 0.8rem; opacity: 0.9;">Professional colors</div>
            </div>
            <div class="feature-card">
                <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">✨</div>
                <div style="font-weight: 700; font-size: 0.95rem; margin-bottom: 0.25rem;">Enhancement Tools</div>
                <div style="font-size: 0.8rem; opacity: 0.9;">Blemish removal & more</div>
            </div>
            <div class="feature-card">
                <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">👔</div>
                <div style="font-weight: 700; font-size: 0.95rem; margin-bottom: 0.25rem;">Formal Attire</div>
                <div style="font-size: 0.8rem; opacity: 0.9;">AI clothing changes</div>
            </div>
        </div>
    </div>
    """

def get_section_header(title, description):
    """Returns a section header HTML"""
    return f"""
    <div class="content-section">
        <div class="section-header">
            <h2 class="section-title">{title}</h2>
            <p class="section-description">{description}</p>
        </div>
    </div>
    """

def get_upload_instructions():
    """Returns web-optimized upload instructions HTML"""
    return """
    <div style="text-align: center; color: #6b7280; margin: 1rem 0; padding: 1rem;">
        <div style="font-size: 1.5rem; margin-bottom: 0.75rem;">📤</div>
        <div style="font-size: 1rem; font-weight: 600; color: #374151; margin-bottom: 0.5rem;">Upload Your Photo</div>
        <div style="font-size: 0.875rem;">Drag and drop or click to select</div>
        <div style="font-size: 0.8rem; color: #9ca3af; margin-top: 0.5rem;">Supports JPG, PNG, WEBP formats</div>
    </div>
    """

def get_quick_tips():
    """Returns quick tips HTML"""
    return """
    <div class="content-section">
        <h3 style="color: #4f46e5; font-weight: 700; margin-bottom: 1rem;">💡 Quick Tips</h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem;">
            <div style="background: #f0f9ff; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #0ea5e9;">
                <div style="font-weight: 600; color: #0c4a6e; margin-bottom: 0.5rem;">🎯 Best Results</div>
                <div style="color: #0e7490; font-size: 0.9rem;">Use high-resolution photos with clear subjects for optimal background removal</div>
            </div>
            <div style="background: #f0fdf4; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #22c55e;">
                <div style="font-weight: 600; color: #14532d; margin-bottom: 0.5rem;">⚡ Replicate API</div>
                <div style="color: #166534; font-size: 0.9rem;">For best quality, use Replicate option with your free API token from replicate.com</div>
            </div>
            <div style="background: #fef7f0; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #f97316;">
                <div style="font-weight: 600; color: #9a3412; margin-bottom: 0.5rem;">🎨 Backgrounds</div>
                <div style="color: #c2410c; font-size: 0.9rem;">Professional blue and white backgrounds work best for business photos</div>
            </div>
        </div>
    </div>
    """

def get_loading_animation():
    """Returns loading animation HTML"""
    return """
    <div style="text-align: center; padding: 2rem;">
        <div style="display: inline-block; width: 40px; height: 40px; border: 4px solid #f3f4f6; border-radius: 50%; border-top-color: #4f46e5; animation: spin 1s ease-in-out infinite;"></div>
        <div style="margin-top: 1rem; color: #6b7280; font-weight: 500;">Processing your image...</div>
        <style>
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
        </style>
    </div>
    """

def get_success_message(message):
    """Returns success message HTML"""
    return f"""
    <div class="status-success">
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span style="font-size: 1.2rem;">✅</span>
            <span style="font-weight: 600;">{message}</span>
        </div>
    </div>
    """

def get_error_message(message):
    """Returns error message HTML"""
    return f"""
    <div class="status-error">
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span style="font-size: 1.2rem;">❌</span>
            <span style="font-weight: 600;">{message}</span>
        </div>
    </div>
    """

def get_coming_soon():
    """Returns coming soon section HTML"""
    return """
    <div class="content-section">
        <div style="text-align: center; padding: 3rem 2rem;">
            <div style="font-size: 4rem; margin-bottom: 1.5rem;">🚀</div>
            <h2 style="color: #4f46e5; font-weight: 700; margin-bottom: 1rem;">Coming Soon!</h2>
            <div style="color: #6b7280; font-size: 1.1rem; line-height: 1.6; max-width: 600px; margin: 0 auto;">
                <div style="margin-bottom: 1rem;">We're working on exciting new features:</div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-top: 2rem;">
                    <div style="background: #f8fafc; padding: 1.5rem; border-radius: 0.75rem; border: 1px solid #e2e8f0;">
                        <div style="font-size: 2rem; margin-bottom: 0.5rem;">✨</div>
                        <div style="font-weight: 600; color: #374151; margin-bottom: 0.5rem;">Blemish Removal</div>
                        <div style="font-size: 0.9rem;">AI-powered skin enhancement</div>
                    </div>
                    <div style="background: #f8fafc; padding: 1.5rem; border-radius: 0.75rem; border: 1px solid #e2e8f0;">
                        <div style="font-size: 2rem; margin-bottom: 0.5rem;">👔</div>
                        <div style="font-weight: 600; color: #374151; margin-bottom: 0.5rem;">Formal Attire</div>
                        <div style="font-size: 0.9rem;">Change clothes with AI</div>
                    </div>
                    <div style="background: #f8fafc; padding: 1.5rem; border-radius: 0.75rem; border: 1px solid #e2e8f0;">
                        <div style="font-size: 2rem; margin-bottom: 0.5rem;">🎭</div>
                        <div style="font-weight: 600; color: #374151; margin-bottom: 0.5rem;">More Tools</div>
                        <div style="font-size: 0.9rem;">Advanced editing features</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """
