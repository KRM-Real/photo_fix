/**
 * Image Enhancement Library
 * Provides functionality for blemish removal, noise reduction, and quality improvement
 */

export interface EnhancementOptions {
  blemishRemoval: boolean;
  noiseReduction: boolean;
  sharpen: boolean;
  brightnessAdjust: number; // -100 to 100
  contrastAdjust: number; // -100 to 100
  saturationAdjust: number; // -100 to 100
}

export const defaultEnhancementOptions: EnhancementOptions = {
  blemishRemoval: true,
  noiseReduction: true,
  sharpen: true,
  brightnessAdjust: 0,
  contrastAdjust: 0,
  saturationAdjust: 0,
};

/**
 * Apply Gaussian blur for noise reduction
 */
function applyGaussianBlur(imageData: ImageData, radius: number): ImageData {
  const data = imageData.data;
  const width = imageData.width;
  const height = imageData.height;
  const output = new Uint8ClampedArray(data);

  const sigma = radius / 3;
  const kernel = createGaussianKernel(radius, sigma);
  const kernelSize = kernel.length;
  const halfKernel = Math.floor(kernelSize / 2);

  // Apply horizontal blur
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      let r = 0, g = 0, b = 0, a = 0;
      let weightSum = 0;

      for (let kx = -halfKernel; kx <= halfKernel; kx++) {
        const px = Math.min(Math.max(x + kx, 0), width - 1);
        const weight = kernel[kx + halfKernel];
        const idx = (y * width + px) * 4;

        r += data[idx] * weight;
        g += data[idx + 1] * weight;
        b += data[idx + 2] * weight;
        a += data[idx + 3] * weight;
        weightSum += weight;
      }

      const idx = (y * width + x) * 4;
      output[idx] = r / weightSum;
      output[idx + 1] = g / weightSum;
      output[idx + 2] = b / weightSum;
      output[idx + 3] = a / weightSum;
    }
  }

  // Apply vertical blur
  const finalOutput = new Uint8ClampedArray(output);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      let r = 0, g = 0, b = 0, a = 0;
      let weightSum = 0;

      for (let ky = -halfKernel; ky <= halfKernel; ky++) {
        const py = Math.min(Math.max(y + ky, 0), height - 1);
        const weight = kernel[ky + halfKernel];
        const idx = (py * width + x) * 4;

        r += output[idx] * weight;
        g += output[idx + 1] * weight;
        b += output[idx + 2] * weight;
        a += output[idx + 3] * weight;
        weightSum += weight;
      }

      const idx = (y * width + x) * 4;
      finalOutput[idx] = r / weightSum;
      finalOutput[idx + 1] = g / weightSum;
      finalOutput[idx + 2] = b / weightSum;
      finalOutput[idx + 3] = a / weightSum;
    }
  }

  return new ImageData(finalOutput, width, height);
}

/**
 * Create Gaussian kernel for blur
 */
function createGaussianKernel(radius: number, sigma: number): number[] {
  const size = radius * 2 + 1;
  const kernel = new Array(size);
  let sum = 0;

  for (let i = 0; i < size; i++) {
    const x = i - radius;
    kernel[i] = Math.exp(-(x * x) / (2 * sigma * sigma));
    sum += kernel[i];
  }

  // Normalize
  for (let i = 0; i < size; i++) {
    kernel[i] /= sum;
  }

  return kernel;
}

/**
 * Apply unsharp mask for sharpening
 */
function applySharpen(imageData: ImageData, strength: number = 0.5): ImageData {
  const data = imageData.data;
  const width = imageData.width;
  const height = imageData.height;
  const output = new Uint8ClampedArray(data);

  // Sharpening kernel
  const kernel = [
    0, -1, 0,
    -1, 5, -1,
    0, -1, 0
  ];

  for (let y = 1; y < height - 1; y++) {
    for (let x = 1; x < width - 1; x++) {
      for (let c = 0; c < 3; c++) { // RGB channels only
        let sum = 0;
        for (let ky = -1; ky <= 1; ky++) {
          for (let kx = -1; kx <= 1; kx++) {
            const idx = ((y + ky) * width + (x + kx)) * 4 + c;
            const kernelIdx = (ky + 1) * 3 + (kx + 1);
            sum += data[idx] * kernel[kernelIdx];
          }
        }

        const idx = (y * width + x) * 4 + c;
        const original = data[idx];
        const sharpened = Math.max(0, Math.min(255, sum));
        output[idx] = original + (sharpened - original) * strength;
      }
    }
  }

  return new ImageData(output, width, height);
}

/**
 * Remove blemishes using median filter
 */
function removeBlemishes(imageData: ImageData, intensity: number = 0.3): ImageData {
  const data = imageData.data;
  const width = imageData.width;
  const height = imageData.height;
  const output = new Uint8ClampedArray(data);

  const radius = 2; // Small radius for blemish detection

  for (let y = radius; y < height - radius; y++) {
    for (let x = radius; x < width - radius; x++) {
      // Collect neighboring pixels
      const neighbors: number[][] = [[], [], []]; // R, G, B

      for (let dy = -radius; dy <= radius; dy++) {
        for (let dx = -radius; dx <= radius; dx++) {
          const idx = ((y + dy) * width + (x + dx)) * 4;
          neighbors[0].push(data[idx]);     // R
          neighbors[1].push(data[idx + 1]); // G
          neighbors[2].push(data[idx + 2]); // B
        }
      }

      // Calculate median for each channel
      const medianR = getMedian(neighbors[0]);
      const medianG = getMedian(neighbors[1]);
      const medianB = getMedian(neighbors[2]);

      const idx = (y * width + x) * 4;
      const currentR = data[idx];
      const currentG = data[idx + 1];
      const currentB = data[idx + 2];

      // Check if pixel is significantly different from median (potential blemish)
      const diffR = Math.abs(currentR - medianR);
      const diffG = Math.abs(currentG - medianG);
      const diffB = Math.abs(currentB - medianB);
      const avgDiff = (diffR + diffG + diffB) / 3;

      if (avgDiff > 30) { // Threshold for blemish detection
        // Blend with median
        output[idx] = currentR + (medianR - currentR) * intensity;
        output[idx + 1] = currentG + (medianG - currentG) * intensity;
        output[idx + 2] = currentB + (medianB - currentB) * intensity;
      }
    }
  }

  return new ImageData(output, width, height);
}

/**
 * Get median value from array
 */
function getMedian(arr: number[]): number {
  const sorted = arr.slice().sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

/**
 * Adjust brightness, contrast, and saturation
 */
function adjustImageProperties(
  imageData: ImageData,
  brightness: number,
  contrast: number,
  saturation: number
): ImageData {
  const data = imageData.data;
  const output = new Uint8ClampedArray(data);

  // Convert adjustments to usable ranges
  const brightnessAdjust = brightness * 2.55; // -255 to 255
  const contrastFactor = (259 * (contrast + 255)) / (255 * (259 - contrast));
  const saturationFactor = (saturation + 100) / 100;

  for (let i = 0; i < data.length; i += 4) {
    let r = data[i];
    let g = data[i + 1];
    let b = data[i + 2];

    // Apply brightness
    r += brightnessAdjust;
    g += brightnessAdjust;
    b += brightnessAdjust;

    // Apply contrast
    r = contrastFactor * (r - 128) + 128;
    g = contrastFactor * (g - 128) + 128;
    b = contrastFactor * (b - 128) + 128;

    // Apply saturation
    if (saturation !== 0) {
      // Convert to grayscale
      const gray = 0.299 * r + 0.587 * g + 0.114 * b;
      r = gray + (r - gray) * saturationFactor;
      g = gray + (g - gray) * saturationFactor;
      b = gray + (b - gray) * saturationFactor;
    }

    // Clamp values
    output[i] = Math.max(0, Math.min(255, r));
    output[i + 1] = Math.max(0, Math.min(255, g));
    output[i + 2] = Math.max(0, Math.min(255, b));
    output[i + 3] = data[i + 3]; // Keep alpha unchanged
  }

  return new ImageData(output, imageData.width, imageData.height);
}

/**
 * Main enhancement function
 */
export async function enhanceImage(
  imageFile: File,
  options: EnhancementOptions = defaultEnhancementOptions
): Promise<File> {
  return new Promise((resolve, reject) => {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const img = new Image();

    if (!ctx) {
      reject(new Error('Could not get 2d context'));
      return;
    }

    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      ctx.drawImage(img, 0, 0);

      let imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);

      // Apply enhancements in order
      if (options.blemishRemoval) {
        imageData = removeBlemishes(imageData, 0.4);
      }

      if (options.noiseReduction) {
        imageData = applyGaussianBlur(imageData, 1);
      }

      if (options.sharpen) {
        imageData = applySharpen(imageData, 0.3);
      }

      // Apply color adjustments
      if (
        options.brightnessAdjust !== 0 ||
        options.contrastAdjust !== 0 ||
        options.saturationAdjust !== 0
      ) {
        imageData = adjustImageProperties(
          imageData,
          options.brightnessAdjust,
          options.contrastAdjust,
          options.saturationAdjust
        );
      }

      // Put enhanced image data back to canvas
      ctx.putImageData(imageData, 0, 0);

      // Convert to file
      canvas.toBlob((blob) => {
        if (blob) {
          const enhancedFile = new File([blob], `enhanced-${imageFile.name}`, {
            type: 'image/png'
          });
          resolve(enhancedFile);
        } else {
          reject(new Error('Failed to create enhanced image blob'));
        }
      }, 'image/png');
    };

    img.onerror = () => reject(new Error('Failed to load image'));
    img.src = URL.createObjectURL(imageFile);
  });
}

/**
 * Auto-enhance function with preset optimal settings
 */
export async function autoEnhanceImage(imageFile: File): Promise<File> {
  const autoOptions: EnhancementOptions = {
    blemishRemoval: true,
    noiseReduction: true,
    sharpen: true,
    brightnessAdjust: 5,
    contrastAdjust: 10,
    saturationAdjust: 8,
  };

  return enhanceImage(imageFile, autoOptions);
}
