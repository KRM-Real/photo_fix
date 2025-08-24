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
  thumbnail: string;
  description: string;
  overlayMask?: string; // For precise placement
}

// Function to generate a placeholder thumbnail
function generatePlaceholderThumbnail(name: string, gender: 'male' | 'female'): string {
  const canvas = document.createElement('canvas');
  canvas.width = 120;
  canvas.height = 160;
  const ctx = canvas.getContext('2d')!;
  
  // Background gradient
  const gradient = ctx.createLinearGradient(0, 0, 0, 160);
  gradient.addColorStop(0, gender === 'male' ? '#3B82F6' : '#EC4899');
  gradient.addColorStop(1, gender === 'male' ? '#1E40AF' : '#BE185D');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 120, 160);
  
  // Person silhouette
  ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
  ctx.beginPath();
  // Head
  ctx.arc(60, 40, 15, 0, Math.PI * 2);
  ctx.fill();
  
  // Body
  ctx.fillRect(45, 55, 30, 50);
  
  // Arms
  ctx.fillRect(35, 60, 10, 35);
  ctx.fillRect(75, 60, 10, 35);
  
  // Legs
  ctx.fillRect(48, 105, 8, 35);
  ctx.fillRect(64, 105, 8, 35);
  
  return canvas.toDataURL();
}

// Predefined attire templates
export const attireTemplates: AttireTemplate[] = [
  // Male Formal
  {
    id: 'male-formal-suit-black',
    name: 'Black Business Suit',
    gender: 'male',
    type: 'formal',
    imageUrl: '/attire/male-formal-black-suit.png',
    thumbnail: generatePlaceholderThumbnail('Black Business Suit', 'male'),
    description: 'Classic black business suit with tie',
  },
  {
    id: 'male-formal-suit-navy',
    name: 'Navy Business Suit',
    gender: 'male',
    type: 'formal',
    imageUrl: '/attire/male-formal-navy-suit.png',
    thumbnail: generatePlaceholderThumbnail('Navy Business Suit', 'male'),
    description: 'Professional navy blue suit',
  },
  {
    id: 'male-formal-tuxedo',
    name: 'Black Tuxedo',
    gender: 'male',
    type: 'formal',
    imageUrl: '/attire/male-formal-tuxedo.png',
    thumbnail: generatePlaceholderThumbnail('Black Tuxedo', 'male'),
    description: 'Elegant black tuxedo for special occasions',
  },

  // Male Semi-Formal
  {
    id: 'male-semi-blazer-khaki',
    name: 'Blazer with Khaki Pants',
    gender: 'male',
    type: 'semi-formal',
    imageUrl: '/attire/male-semi-blazer-khaki.png',
    thumbnail: generatePlaceholderThumbnail('Blazer with Khaki Pants', 'male'),
    description: 'Smart casual blazer with khaki chinos',
  },
  {
    id: 'male-semi-shirt-jeans',
    name: 'Dress Shirt with Jeans',
    gender: 'male',
    type: 'semi-formal',
    imageUrl: '/attire/male-semi-shirt-jeans.png',
    thumbnail: generatePlaceholderThumbnail('Dress Shirt with Jeans', 'male'),
    description: 'Casual dress shirt with dark jeans',
  },

  // Male Polo Shirts
  {
    id: 'male-polo-white',
    name: 'White Polo Shirt',
    gender: 'male',
    type: 'polo-shirt',
    imageUrl: '/attire/male-polo-white.png',
    thumbnail: generatePlaceholderThumbnail('White Polo Shirt', 'male'),
    description: 'Classic white polo shirt',
  },
  {
    id: 'male-polo-navy',
    name: 'Navy Polo Shirt',
    gender: 'male',
    type: 'polo-shirt',
    imageUrl: '/attire/male-polo-navy.png',
    thumbnail: generatePlaceholderThumbnail('Navy Polo Shirt', 'male'),
    description: 'Navy blue polo shirt',
  },

  // Female Formal
  {
    id: 'female-formal-suit-black',
    name: 'Black Business Suit',
    gender: 'female',
    type: 'formal',
    imageUrl: '/attire/female-formal-black-suit.png',
    thumbnail: generatePlaceholderThumbnail('Black Business Suit', 'female'),
    description: 'Professional black blazer with dress pants',
  },
  {
    id: 'female-formal-dress-navy',
    name: 'Navy Business Dress',
    gender: 'female',
    type: 'formal',
    imageUrl: '/attire/female-formal-navy-dress.png',
    thumbnail: generatePlaceholderThumbnail('Navy Business Dress', 'female'),
    description: 'Elegant navy business dress',
  },
  {
    id: 'female-formal-blazer-skirt',
    name: 'Blazer with Skirt',
    gender: 'female',
    type: 'formal',
    imageUrl: '/attire/female-formal-blazer-skirt.png',
    thumbnail: generatePlaceholderThumbnail('Blazer with Skirt', 'female'),
    description: 'Classic blazer with pencil skirt',
  },

  // Female Semi-Formal
  {
    id: 'female-semi-blouse-pants',
    name: 'Blouse with Dress Pants',
    gender: 'female',
    type: 'semi-formal',
    imageUrl: '/attire/female-semi-blouse-pants.png',
    thumbnail: generatePlaceholderThumbnail('Blouse with Dress Pants', 'female'),
    description: 'Elegant blouse with tailored pants',
  },
  {
    id: 'female-semi-cardigan-dress',
    name: 'Cardigan with Dress',
    gender: 'female',
    type: 'semi-formal',
    imageUrl: '/attire/female-semi-cardigan-dress.png',
    thumbnail: generatePlaceholderThumbnail('Cardigan with Dress', 'female'),
    description: 'Cozy cardigan with midi dress',
  },

  // Female Polo Shirts
  {
    id: 'female-polo-white',
    name: 'White Polo Shirt',
    gender: 'female',
    type: 'polo-shirt',
    imageUrl: '/attire/female-polo-white.png',
    thumbnail: generatePlaceholderThumbnail('White Polo Shirt', 'female'),
    description: 'Classic white polo shirt',
  },
  {
    id: 'female-polo-pink',
    name: 'Pink Polo Shirt',
    gender: 'female',
    type: 'polo-shirt',
    imageUrl: '/attire/female-polo-pink.png',
    thumbnail: generatePlaceholderThumbnail('Pink Polo Shirt', 'female'),
    description: 'Soft pink polo shirt',
  },
];

/**
 * Get attire templates based on gender
 */
export function getAttireTemplates(gender: 'male' | 'female'): AttireTemplate[] {
  return attireTemplates.filter(template => template.gender === gender);
}

/**
 * Get attire templates by type and gender
 */
export function getAttireTemplatesByType(
  gender: 'male' | 'female',
  type: 'formal' | 'semi-formal' | 'polo-shirt'
): AttireTemplate[] {
  return attireTemplates.filter(
    template => template.gender === gender && template.type === type
  );
}

/**
 * Detect person boundaries in an image
 */
function detectPersonBoundaries(imageData: ImageData): {
  torso: { x: number; y: number; width: number; height: number };
  shoulders: { x: number; y: number; width: number; height: number };
} {
  const { width, height } = imageData;
  
  // Simple heuristic-based detection (in real app, use ML)
  const centerX = width / 2;
  const centerY = height / 2;
  
  // Estimate torso area (center of image)
  const torso = {
    x: Math.floor(centerX - width * 0.15),
    y: Math.floor(centerY - height * 0.1),
    width: Math.floor(width * 0.3),
    height: Math.floor(height * 0.4),
  };
  
  // Estimate shoulder area (upper center)
  const shoulders = {
    x: Math.floor(centerX - width * 0.2),
    y: Math.floor(centerY - height * 0.25),
    width: Math.floor(width * 0.4),
    height: Math.floor(height * 0.15),
  };
  
  return { torso, shoulders };
}

/**
 * Draw attire overlay on canvas
 */
function drawAttireOverlay(
  ctx: CanvasRenderingContext2D,
  template: AttireTemplate,
  x: number,
  y: number,
  width: number,
  height: number
): void {
  // Save current context
  ctx.save();
  
  // Set blend mode for natural integration
  ctx.globalCompositeOperation = 'multiply';
  ctx.globalAlpha = 0.7;
  
  // Draw based on attire type
  if (template.type === 'formal') {
    // Formal suit - dark colors
    if (template.name.includes('Black')) {
      ctx.fillStyle = '#1a1a1a';
    } else if (template.name.includes('Navy')) {
      ctx.fillStyle = '#1e3a8a';
    } else {
      ctx.fillStyle = '#374151';
    }
  } else if (template.type === 'semi-formal') {
    // Semi-formal - medium colors
    if (template.name.includes('Blazer')) {
      ctx.fillStyle = '#4b5563';
    } else {
      ctx.fillStyle = '#6b7280';
    }
  } else {
    // Polo shirt - lighter colors
    if (template.name.includes('White')) {
      ctx.fillStyle = '#f9fafb';
    } else if (template.name.includes('Navy')) {
      ctx.fillStyle = '#3730a3';
    } else if (template.name.includes('Pink')) {
      ctx.fillStyle = '#ec4899';
    } else {
      ctx.fillStyle = '#6366f1';
    }
  }
  
  // Draw the attire shape
  ctx.fillRect(x, y, width, height);
  
  // Add some detail for formal wear
  if (template.type === 'formal') {
    // Draw collar
    ctx.fillStyle = '#ffffff';
    ctx.globalAlpha = 0.8;
    const collarHeight = height * 0.15;
    ctx.fillRect(x + width * 0.3, y, width * 0.4, collarHeight);
    
    // Draw tie
    if (template.gender === 'male') {
      ctx.fillStyle = '#991b1b';
      ctx.globalAlpha = 0.9;
      const tieWidth = width * 0.1;
      const tieHeight = height * 0.6;
      ctx.fillRect(x + width * 0.45, y + collarHeight, tieWidth, tieHeight);
    }
  }
  
  // Restore context
  ctx.restore();
}

/**
 * Apply attire to an image
 */
export async function applyAttire(
  originalImage: File,
  attireTemplate: AttireTemplate,
  options: AttireOptions = defaultAttireOptions
): Promise<File> {
  return new Promise((resolve, reject) => {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    
    if (!ctx) {
      reject(new Error('Could not get 2D context'));
      return;
    }

    const originalImg = new Image();
    
    originalImg.onload = () => {
      canvas.width = originalImg.width;
      canvas.height = originalImg.height;
      
      // Draw original image
      ctx.drawImage(originalImg, 0, 0);
      
      try {
        // Get person boundaries
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const { torso, shoulders } = detectPersonBoundaries(imageData);
        
        // Calculate attire placement based on detected boundaries
        let attireX, attireY, attireWidth, attireHeight;
        
        if (attireTemplate.type === 'formal') {
          // Formal attire covers torso and shoulders
          attireX = Math.min(torso.x, shoulders.x);
          attireY = shoulders.y;
          attireWidth = Math.max(torso.width, shoulders.width);
          attireHeight = torso.y + torso.height - shoulders.y;
        } else if (attireTemplate.type === 'semi-formal') {
          // Semi-formal covers mostly torso
          attireX = torso.x;
          attireY = torso.y - torso.height * 0.1;
          attireWidth = torso.width;
          attireHeight = torso.height * 1.2;
        } else {
          // Polo shirt covers upper torso
          attireX = shoulders.x;
          attireY = shoulders.y;
          attireWidth = shoulders.width;
          attireHeight = shoulders.height + torso.height * 0.3;
        }
        
        // Draw attire overlay
        drawAttireOverlay(ctx, attireTemplate, attireX, attireY, attireWidth, attireHeight);
        
        // Convert to blob and create file
        canvas.toBlob((blob) => {
          if (blob) {
            const file = new File([blob], 'attire-changed.png', { type: 'image/png' });
            resolve(file);
          } else {
            reject(new Error('Failed to create attire image'));
          }
        }, 'image/png', 0.9);
        
      } catch (error) {
        reject(new Error(`Failed to apply attire: ${error}`));
      }
    };
    
    originalImg.onerror = () => reject(new Error('Failed to load original image'));
    originalImg.src = URL.createObjectURL(originalImage);
  });
}
