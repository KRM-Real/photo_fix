/**
 * Attire Changer Library
 * Provides functionality for changing clothing in images based on gender and attire type
 */

export interface AttireOptions {
  gender: 'male' | 'female';
  attireType: 'formal' | 'semi-formal' | 'polo-shirt';
  preserveFace: boolean;
  preserveHands: boolean;
  blendMode: 'natural' | 'smooth' | 'precise';
}

export const defaultAttireOptions: AttireOptions = {
  gender: 'male',
  attireType: 'formal',
  preserveFace: true,
  preserveHands: true,
  blendMode: 'natural',
};

export interface AttireTemplate {
  id: string;
  name: string;
  gender: 'male' | 'female';
  type: 'formal' | 'semi-formal' | 'polo-shirt';
  imageUrl: string;
  thumbnail?: string;
  description: string;
  overlayMask?: string; // For precise placement
}

// Predefined attire templates based on your uploaded files
export const attireTemplates: AttireTemplate[] = [
  // Male Formal
  {
    id: 'male-formal-black',
    name: 'Black Formal',
    gender: 'male',
    type: 'formal',
    imageUrl: '/attire/male-formal-black.png',
    thumbnail: '/attire/male-formal-black.png',
    description: 'Professional black formal attire',
  },

  // Male Semi-Formal
  {
    id: 'male-semi-blue',
    name: 'Blue Semi-Formal',
    gender: 'male',
    type: 'semi-formal',
    imageUrl: '/attire/male-semi-blue.png',
    thumbnail: '/attire/male-semi-blue.png',
    description: 'Casual blue semi-formal attire',
  },
  {
    id: 'male-semi-white',
    name: 'White Semi-Formal',
    gender: 'male',
    type: 'semi-formal',
    imageUrl: '/attire/male-semi-white.png',
    thumbnail: '/attire/male-semi-white.png',
    description: 'Clean white semi-formal attire',
  },

  // Female Formal
  {
    id: 'female-formal-black',
    name: 'Black Formal',
    gender: 'female',
    type: 'formal',
    imageUrl: '/attire/female-formal-black.png',
    thumbnail: '/attire/female-formal-black.png',
    description: 'Elegant black formal attire',
  },
];

// Get templates by gender
export function getAttireTemplates(gender: 'male' | 'female'): AttireTemplate[] {
  return attireTemplates.filter(template => template.gender === gender);
}

// Helper function to get average skin color from head area
function getSkinColorFromHead(ctx: CanvasRenderingContext2D, head: { x: number; y: number; width: number; height: number }): { r: number; g: number; b: number } {
  const imageData = ctx.getImageData(head.x, head.y, head.width, head.height);
  const data = imageData.data;
  
  let totalR = 0, totalG = 0, totalB = 0, count = 0;
  
  // Sample pixels from the head area
  for (let i = 0; i < data.length; i += 16) { // Sample every 4th pixel
    const r = data[i];
    const g = data[i + 1];
    const b = data[i + 2];
    
    // Filter for skin-like colors
    if (r > 100 && g > 80 && b > 60 && r > b && g > b) {
      totalR += r;
      totalG += g;
      totalB += b;
      count++;
    }
  }
  
  if (count === 0) {
    // Fallback to average skin tone
    return { r: 220, g: 180, b: 140 };
  }
  
  return {
    r: Math.round(totalR / count),
    g: Math.round(totalG / count),
    b: Math.round(totalB / count)
  };
}

// Get templates by gender and type
export function getAttireTemplatesByType(gender: 'male' | 'female', type: 'formal' | 'semi-formal' | 'polo-shirt'): AttireTemplate[] {
  return attireTemplates.filter(template => template.gender === gender && template.type === type);
}

// Detect person boundaries using image analysis
async function detectPersonBoundaries(imageBlob: Blob): Promise<{
  torso: { x: number; y: number; width: number; height: number };
  head: { x: number; y: number; width: number; height: number };
  clothing: { x: number; y: number; width: number; height: number };
}> {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d')!;
      canvas.width = img.width;
      canvas.height = img.height;
      ctx.drawImage(img, 0, 0);

      const imgWidth = img.width;
      const imgHeight = img.height;
      const centerX = imgWidth / 2;

      // Analyze the image to find clothing boundaries
      const imageData = ctx.getImageData(0, 0, imgWidth, imgHeight);
      const data = imageData.data;

      // Find the actual clothing area by detecting color regions
      let clothingTop = imgHeight * 0.3;
      let clothingBottom = imgHeight * 0.8;
      let clothingLeft = centerX - imgWidth * 0.3;
      let clothingRight = centerX + imgWidth * 0.3;

      // Scan for clothing boundaries (look for consistent color regions)
      for (let y = Math.floor(imgHeight * 0.25); y < Math.floor(imgHeight * 0.9); y += 5) {
        for (let x = Math.floor(centerX - imgWidth * 0.35); x < Math.floor(centerX + imgWidth * 0.35); x += 5) {
          const idx = (y * imgWidth + x) * 4;
          const r = data[idx];
          const g = data[idx + 1];
          const b = data[idx + 2];
          
          // Look for clothing colors (not skin tones)
          if (!(r > 180 && g > 140 && b > 120)) { // Not skin color
            clothingTop = Math.min(clothingTop, y);
            clothingBottom = Math.max(clothingBottom, y);
            clothingLeft = Math.min(clothingLeft, x);
            clothingRight = Math.max(clothingRight, x);
          }
        }
      }

      const boundaries = {
        head: {
          x: centerX - imgWidth * 0.15,
          y: imgHeight * 0.05,
          width: imgWidth * 0.3,
          height: imgHeight * 0.25,
        },
        torso: {
          x: centerX - imgWidth * 0.25,
          y: imgHeight * 0.3,
          width: imgWidth * 0.5,
          height: imgHeight * 0.5,
        },
        clothing: {
          x: clothingLeft,
          y: clothingTop,
          width: clothingRight - clothingLeft,
          height: clothingBottom - clothingTop,
        }
      };

      console.log('Detected boundaries:', boundaries);
      resolve(boundaries);
    };
    img.src = URL.createObjectURL(imageBlob);
  });
}

// Main function to apply attire to an image
export async function applyAttire(
  imageBlob: Blob,
  template: AttireTemplate,
  options: AttireOptions,
  debugMode: boolean = false
): Promise<Blob> {
  return new Promise(async (resolve, reject) => {
    try {
      // Load the original image
      const originalImg = new Image();
      originalImg.crossOrigin = 'anonymous';
      
      originalImg.onload = async () => {
        try {
          // Create canvas for processing
          const canvas = document.createElement('canvas');
          const ctx = canvas.getContext('2d')!;
          canvas.width = originalImg.width;
          canvas.height = originalImg.height;

          // Draw original image
          ctx.drawImage(originalImg, 0, 0);

          // Detect person boundaries
          const boundaries = await detectPersonBoundaries(imageBlob);

          // Load attire image
          const attireImg = new Image();
          attireImg.crossOrigin = 'anonymous';
          
          attireImg.onload = () => {
            try {
              console.log('Attire image loaded:', attireImg.width, 'x', attireImg.height);
              
              // Get clothing boundaries instead of torso
              const { clothing, head } = boundaries;
              console.log('Clothing area:', clothing);
              console.log('Head area:', head);
              
              // Step 1: Create a mask for the clothing area
              const maskCanvas = document.createElement('canvas');
              const maskCtx = maskCanvas.getContext('2d')!;
              maskCanvas.width = originalImg.width;
              maskCanvas.height = originalImg.height;
              
              // Fill mask with the clothing area
              maskCtx.fillStyle = 'white';
              maskCtx.fillRect(clothing.x, clothing.y, clothing.width, clothing.height);
              
              // Step 2: Remove existing clothing by painting skin-like color
              const skinColor = getSkinColorFromHead(ctx, head);
              console.log('Detected skin color:', skinColor);
              
              ctx.fillStyle = `rgb(${skinColor.r}, ${skinColor.g}, ${skinColor.b})`;
              ctx.fillRect(clothing.x, clothing.y, clothing.width, clothing.height);
              
              // Step 3: Apply new attire
              const attireAspectRatio = attireImg.width / attireImg.height;
              const clothingAspectRatio = clothing.width / clothing.height;
              
              let newAttireWidth, newAttireHeight;
              if (attireAspectRatio > clothingAspectRatio) {
                // Attire is wider - fit to clothing width
                newAttireWidth = clothing.width;
                newAttireHeight = clothing.width / attireAspectRatio;
              } else {
                // Attire is taller - fit to clothing height
                newAttireHeight = clothing.height;
                newAttireWidth = clothing.height * attireAspectRatio;
              }
              
              // Center the attire in the clothing area
              const attireX = clothing.x + (clothing.width - newAttireWidth) / 2;
              const attireY = clothing.y + (clothing.height - newAttireHeight) / 2;
              
              console.log('New attire dimensions:', { 
                x: attireX, 
                y: attireY, 
                width: newAttireWidth, 
                height: newAttireHeight 
              });

              // Debug: Draw boundaries
              if (debugMode) {
                ctx.strokeStyle = 'red';
                ctx.lineWidth = 2;
                ctx.strokeRect(clothing.x, clothing.y, clothing.width, clothing.height);
                ctx.strokeStyle = 'blue';
                ctx.strokeRect(attireX, attireY, newAttireWidth, newAttireHeight);
                ctx.strokeStyle = 'green';
                ctx.strokeRect(head.x, head.y, head.width, head.height);
              }

              // Draw the new attire
              ctx.save();
              ctx.globalCompositeOperation = 'source-over';
              ctx.globalAlpha = 1.0;
              
              ctx.drawImage(
                attireImg,
                attireX,
                attireY,
                newAttireWidth,
                newAttireHeight
              );
              
              ctx.restore();

              console.log('Attire replacement completed');

              // Convert canvas to blob
              canvas.toBlob((blob) => {
                if (blob) {
                  resolve(blob);
                } else {
                  reject(new Error('Failed to create attire blob'));
                }
              }, 'image/png', 0.95);

            } catch (error) {
              console.error('Error in attire replacement:', error);
              reject(error);
            }
          };

          attireImg.onerror = () => {
            reject(new Error(`Failed to load attire image: ${template.imageUrl}`));
          };

          // Load attire image
          attireImg.src = template.imageUrl;

        } catch (error) {
          reject(error);
        }
      };

      originalImg.onerror = () => {
        reject(new Error('Failed to load original image'));
      };

      // Load original image
      originalImg.src = URL.createObjectURL(imageBlob);

    } catch (error) {
      reject(error);
    }
  });
}
