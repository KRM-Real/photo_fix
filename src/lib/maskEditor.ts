/**
 * Mask Editor Library
 * Provides functionality for manually editing masks with erase and restore tools
 */

export interface Point {
  x: number;
  y: number;
}

export interface BrushSettings {
  size: number;
  hardness: number; // 0-1, where 1 is completely hard edge
  opacity: number; // 0-1
}

export const defaultBrushSettings: BrushSettings = {
  size: 20,
  hardness: 0.8,
  opacity: 1.0,
};

export class MaskEditor {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private maskData: ImageData;
  private originalImageData: ImageData;
  public isDrawing: boolean = false;
  private lastPoint: Point | null = null;
  private brushSettings: BrushSettings = defaultBrushSettings;
  private currentTool: 'erase' | 'restore' = 'erase';
  private showGuide: boolean = true;
  private guideOpacity: number = 0.3;

  constructor(canvas: HTMLCanvasElement, maskImageData: ImageData, originalImageData: ImageData) {
    this.canvas = canvas;
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Could not get 2D context');
    this.ctx = ctx;
    
    // Make copies of the image data to avoid modifying originals
    this.maskData = new ImageData(
      new Uint8ClampedArray(maskImageData.data),
      maskImageData.width,
      maskImageData.height
    );
    this.originalImageData = new ImageData(
      new Uint8ClampedArray(originalImageData.data),
      originalImageData.width,
      originalImageData.height
    );
    
    this.setupCanvas();
  }

  private setupCanvas() {
    this.canvas.width = this.maskData.width;
    this.canvas.height = this.maskData.height;
    
    // Set canvas display size to fit container while maintaining aspect ratio
    const maxWidth = 700;
    const maxHeight = 500;
    const aspectRatio = this.canvas.width / this.canvas.height;
    
    let displayWidth = Math.min(maxWidth, this.canvas.width);
    let displayHeight = displayWidth / aspectRatio;
    
    if (displayHeight > maxHeight) {
      displayHeight = maxHeight;
      displayWidth = displayHeight * aspectRatio;
    }
    
    // Ensure minimum size for usability
    if (displayWidth < 300) {
      displayWidth = 300;
      displayHeight = displayWidth / aspectRatio;
    }
    
    this.canvas.style.width = `${displayWidth}px`;
    this.canvas.style.height = `${displayHeight}px`;
    this.canvas.style.display = 'block';
    
    this.updateDisplay();
  }

  public updateDisplay() {
    // Clear canvas
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    
    // First, draw a checkered background pattern for transparency visualization
    this.drawCheckeredBackground();
    
    // Draw guide (original image) if enabled
    if (this.showGuide) {
      this.ctx.save();
      this.ctx.globalAlpha = this.guideOpacity;
      this.ctx.putImageData(this.originalImageData, 0, 0);
      this.ctx.restore();
    }
    
    // Create masked image
    const maskedImageData = new ImageData(
      new Uint8ClampedArray(this.originalImageData.data),
      this.originalImageData.width,
      this.originalImageData.height
    );
    
    // Apply mask to create the final composite
    for (let i = 0; i < this.maskData.data.length; i += 4) {
      const alpha = this.maskData.data[i]; // Using red channel as alpha
      const pixelIndex = i / 4;
      const compositeIndex = pixelIndex * 4;
      maskedImageData.data[compositeIndex + 3] = alpha; // Set alpha channel
    }
    
    // Draw the masked image over the guide
    this.ctx.save();
    this.ctx.globalCompositeOperation = 'source-over';
    this.ctx.putImageData(maskedImageData, 0, 0);
    this.ctx.restore();
  }

  private drawCheckeredBackground() {
    const tileSize = 20;
    this.ctx.fillStyle = '#f0f0f0';
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    
    this.ctx.fillStyle = '#e0e0e0';
    for (let x = 0; x < this.canvas.width; x += tileSize) {
      for (let y = 0; y < this.canvas.height; y += tileSize) {
        if ((x / tileSize + y / tileSize) % 2 === 1) {
          this.ctx.fillRect(x, y, tileSize, tileSize);
        }
      }
    }
  }

  public setShowGuide(show: boolean) {
    this.showGuide = show;
    this.updateDisplay();
  }

  public setGuideOpacity(opacity: number) {
    this.guideOpacity = Math.max(0, Math.min(1, opacity));
    this.updateDisplay();
  }

  public getShowGuide(): boolean {
    return this.showGuide;
  }

  public getGuideOpacity(): number {
    return this.guideOpacity;
  }

  public drawCursorPreview(x: number, y: number) {
    // First update the display normally
    this.updateDisplay();
    
    // Save current context state
    this.ctx.save();
    
    // Draw cursor circle
    this.ctx.strokeStyle = this.currentTool === 'erase' ? '#ef4444' : '#22c55e';
    this.ctx.lineWidth = 2;
    this.ctx.setLineDash([5, 5]);
    this.ctx.globalAlpha = 0.8;
    this.ctx.beginPath();
    this.ctx.arc(x, y, this.brushSettings.size / 2, 0, 2 * Math.PI);
    this.ctx.stroke();
    
    // Draw inner circle for hardness
    if (this.brushSettings.hardness < 1) {
      this.ctx.strokeStyle = this.currentTool === 'erase' ? '#fca5a5' : '#86efac';
      this.ctx.lineWidth = 1;
      this.ctx.globalAlpha = 0.6;
      this.ctx.beginPath();
      this.ctx.arc(x, y, (this.brushSettings.size / 2) * this.brushSettings.hardness, 0, 2 * Math.PI);
      this.ctx.stroke();
    }
    
    // Draw center dot
    this.ctx.fillStyle = this.currentTool === 'erase' ? '#ef4444' : '#22c55e';
    this.ctx.globalAlpha = 0.8;
    this.ctx.beginPath();
    this.ctx.arc(x, y, 2, 0, 2 * Math.PI);
    this.ctx.fill();
    
    // Restore context state
    this.ctx.restore();
  }

  public setBrushSettings(settings: Partial<BrushSettings>) {
    this.brushSettings = { ...this.brushSettings, ...settings };
  }

  public setTool(tool: 'erase' | 'restore') {
    this.currentTool = tool;
  }

  public startDrawing(point: Point) {
    this.isDrawing = true;
    this.lastPoint = point;
    this.drawBrushStroke(point, point);
  }

  public continueDrawing(point: Point) {
    if (!this.isDrawing || !this.lastPoint) return;
    
    this.drawBrushStroke(this.lastPoint, point);
    this.lastPoint = point;
  }

  public stopDrawing() {
    this.isDrawing = false;
    this.lastPoint = null;
  }

  private drawBrushStroke(from: Point, to: Point) {
    const distance = Math.sqrt(Math.pow(to.x - from.x, 2) + Math.pow(to.y - from.y, 2));
    const steps = Math.max(1, Math.floor(distance));
    
    for (let i = 0; i <= steps; i++) {
      const t = steps === 0 ? 0 : i / steps;
      const x = Math.round(from.x + (to.x - from.x) * t);
      const y = Math.round(from.y + (to.y - from.y) * t);
      this.applyBrush(x, y);
    }
    
    this.updateDisplay();
  }

  private applyBrush(centerX: number, centerY: number) {
    const radius = this.brushSettings.size / 2;
    const minX = Math.max(0, Math.floor(centerX - radius));
    const maxX = Math.min(this.maskData.width - 1, Math.floor(centerX + radius));
    const minY = Math.max(0, Math.floor(centerY - radius));
    const maxY = Math.min(this.maskData.height - 1, Math.floor(centerY + radius));

    for (let y = minY; y <= maxY; y++) {
      for (let x = minX; x <= maxX; x++) {
        const distance = Math.sqrt(Math.pow(x - centerX, 2) + Math.pow(y - centerY, 2));
        
        if (distance <= radius) {
          const falloff = this.calculateFalloff(distance, radius);
          const strength = falloff * this.brushSettings.opacity;
          
          const index = (y * this.maskData.width + x) * 4;
          const currentAlpha = this.maskData.data[index];
          
          let newAlpha: number;
          if (this.currentTool === 'erase') {
            // Erase: reduce alpha (make transparent)
            newAlpha = Math.max(0, currentAlpha - (255 * strength));
          } else {
            // Restore: increase alpha (make opaque)
            newAlpha = Math.min(255, currentAlpha + (255 * strength));
          }
          
          // Update all channels with the alpha value (grayscale mask)
          this.maskData.data[index] = newAlpha;     // R
          this.maskData.data[index + 1] = newAlpha; // G
          this.maskData.data[index + 2] = newAlpha; // B
          this.maskData.data[index + 3] = 255;      // A
        }
      }
    }
  }

  private calculateFalloff(distance: number, radius: number): number {
    if (distance >= radius) return 0;
    
    const hardnessRadius = radius * this.brushSettings.hardness;
    
    if (distance <= hardnessRadius) {
      return 1; // Full strength within hardness radius
    } else {
      // Smooth falloff beyond hardness radius
      const falloffDistance = distance - hardnessRadius;
      const falloffRange = radius - hardnessRadius;
      return 1 - (falloffDistance / falloffRange);
    }
  }

  public getMaskImageData(): ImageData {
    return new ImageData(
      new Uint8ClampedArray(this.maskData.data),
      this.maskData.width,
      this.maskData.height
    );
  }

  public getMaskAsFile(originalFileName: string): Promise<File> {
    return new Promise((resolve, reject) => {
      const maskCanvas = document.createElement('canvas');
      maskCanvas.width = this.maskData.width;
      maskCanvas.height = this.maskData.height;
      const maskCtx = maskCanvas.getContext('2d');
      
      if (!maskCtx) {
        reject(new Error('Could not get 2D context for mask'));
        return;
      }
      
      maskCtx.putImageData(this.maskData, 0, 0);
      
      maskCanvas.toBlob((blob) => {
        if (blob) {
          const fileName = `${originalFileName.split('.')[0]}-edited-mask.png`;
          const file = new File([blob], fileName, { type: 'image/png' });
          resolve(file);
        } else {
          reject(new Error('Failed to create mask blob'));
        }
      }, 'image/png');
    });
  }

  public getProcessedImageAsFile(originalFileName: string): Promise<File> {
    return new Promise((resolve, reject) => {
      const processedCanvas = document.createElement('canvas');
      processedCanvas.width = this.originalImageData.width;
      processedCanvas.height = this.originalImageData.height;
      const processedCtx = processedCanvas.getContext('2d');
      
      if (!processedCtx) {
        reject(new Error('Could not get 2D context for processed image'));
        return;
      }
      
      // Draw original image
      processedCtx.putImageData(this.originalImageData, 0, 0);
      
      // Apply mask as alpha channel
      const imageData = processedCtx.getImageData(0, 0, processedCanvas.width, processedCanvas.height);
      for (let i = 0; i < this.maskData.data.length; i += 4) {
        const alpha = this.maskData.data[i]; // Using red channel as alpha
        const pixelIndex = i / 4;
        imageData.data[pixelIndex * 4 + 3] = alpha; // Set alpha channel
      }
      processedCtx.putImageData(imageData, 0, 0);
      
      processedCanvas.toBlob((blob) => {
        if (blob) {
          const fileName = `${originalFileName.split('.')[0]}-edited.png`;
          const file = new File([blob], fileName, { type: 'image/png' });
          resolve(file);
        } else {
          reject(new Error('Failed to create processed image blob'));
        }
      }, 'image/png');
    });
  }

  public reset(newMaskData: ImageData) {
    this.maskData = new ImageData(
      new Uint8ClampedArray(newMaskData.data),
      newMaskData.width,
      newMaskData.height
    );
    this.updateDisplay();
  }

  public undo() {
    // This would require implementing an undo stack
    // For now, we'll keep it simple
    console.log('Undo functionality would be implemented here');
  }

  public cleanup() {
    // Clean up any event listeners or resources
    this.isDrawing = false;
    this.lastPoint = null;
  }
}
