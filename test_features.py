#!/usr/bin/env python3
"""
Test script to verify all PhotoFix features are functional
"""

import sys
import traceback
from PIL import Image
import numpy as np

# Import our PhotoFix functions
try:
    from Photofix import (
        remove_bg, 
        remove_blemishes_basic, 
        apply_formal_overlay, 
        solid_background,
        gradient_background,
        enhance_portrait,
        professional_edit,
        smart_crop,
        PRESETS,
        BG_COLORS
    )
    print("✅ All imports successful!")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def create_test_image():
    """Create a simple test image"""
    # Create a 300x300 test image with a simple face-like pattern
    img_array = np.zeros((300, 300, 3), dtype=np.uint8)
    
    # Fill with skin tone
    img_array[:, :] = [220, 180, 140]  # Light skin tone
    
    # Add a simple face shape (circle)
    center_x, center_y = 150, 150
    radius = 80
    
    for y in range(300):
        for x in range(300):
            distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
            if distance < radius:
                # Face area - lighter skin
                img_array[y, x] = [230, 190, 150]
            elif distance < radius + 20:
                # Hair area - dark
                img_array[y, x] = [50, 30, 20]
    
    # Add simple eyes
    eye_y = center_y - 20
    for eye_x in [center_x - 25, center_x + 25]:
        for dy in range(-5, 6):
            for dx in range(-8, 9):
                if 0 <= eye_y + dy < 300 and 0 <= eye_x + dx < 300:
                    img_array[eye_y + dy, eye_x + dx] = [0, 0, 0]  # Black eyes
    
    # Add simple mouth
    mouth_y = center_y + 25
    for dx in range(-15, 16):
        if 0 <= mouth_y < 300 and 0 <= center_x + dx < 300:
            img_array[mouth_y, center_x + dx] = [150, 50, 50]  # Red mouth
    
    return Image.fromarray(img_array)

def test_feature(feature_name, feature_func, *args):
    """Test a single feature"""
    try:
        print(f"🧪 Testing {feature_name}...")
        result = feature_func(*args)
        if result is not None:
            print(f"✅ {feature_name} - SUCCESS")
            return True
        else:
            print(f"❌ {feature_name} - FAILED (returned None)")
            return False
    except Exception as e:
        print(f"❌ {feature_name} - ERROR: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """Test all PhotoFix features"""
    print("🚀 PhotoFix Feature Test Suite")
    print("=" * 50)
    
    # Create test image
    print("📷 Creating test image...")
    test_img = create_test_image()
    
    # Test each feature
    test_results = []
    
    # 1. Background Removal
    test_results.append(
        test_feature("Background Removal", remove_bg, test_img)
    )
    
    # 2. Blemish Removal
    test_results.append(
        test_feature("Blemish Removal", remove_blemishes_basic, test_img, 0.5)
    )
    
    # 3. Solid Background
    test_results.append(
        test_feature("Solid Background", solid_background, test_img, "#FFFFFF", "2x2 in @300DPI (600x600)")
    )
    
    # 4. Gradient Background  
    test_results.append(
        test_feature("Gradient Background", gradient_background, test_img, "#FFFFFF", "#F0F0F0", "2x2 in @300DPI (600x600)")
    )
    
    # 5. Formal Overlay
    test_results.append(
        test_feature("Formal Attire Overlay", apply_formal_overlay, test_img, "2x2 in @300DPI (600x600)", "suit")
    )
    
    # 6. Portrait Enhancement
    test_results.append(
        test_feature("Portrait Enhancement", enhance_portrait, test_img, "2x2 in @300DPI (600x600)", 0.5)
    )
    
    # 7. Professional Pipeline
    test_results.append(
        test_feature("Professional Pipeline", professional_edit, test_img, "2x2 in @300DPI (600x600)", "#FFFFFF", "suit", 0.5)
    )
    
    # 8. Smart Crop
    test_results.append(
        test_feature("Smart Crop", smart_crop, test_img, (300, 300))
    )
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 ALL FEATURES ARE FUNCTIONAL!")
    else:
        print("⚠️  Some features need attention")
    
    # Test data availability
    print("\n📋 CONFIGURATION CHECK:")
    print(f"📐 Available Presets: {len(PRESETS)}")
    print(f"🎨 Available Background Colors: {len(BG_COLORS)}")
    
    for preset_name in PRESETS:
        print(f"   • {preset_name}: {PRESETS[preset_name]}")
    
    print("\n🎨 Background Colors:")
    for color_name, color_value in BG_COLORS.items():
        print(f"   • {color_name}: {color_value}")

if __name__ == "__main__":
    main()
