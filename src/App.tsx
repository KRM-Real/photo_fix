import React, { useEffect, useState, useRef } from "react";
import { initializeModel, processImage } from "./lib/process";
import { enhanceImage, autoEnhanceImage, EnhancementOptions, defaultEnhancementOptions } from "./lib/enhance";
import { MaskEditor, BrushSettings, defaultBrushSettings } from "./lib/maskEditor";

export default function App() {
  const [image, setImage] = useState<{
    id: number;
    file: File;
    maskFile?: File;
    processedFile?: File;
    enhancedFile?: File;
  } | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isEnhancing, setIsEnhancing] = useState(false);
  const [showEnhancementControls, setShowEnhancementControls] = useState(false);
  const [showMaskEditor, setShowMaskEditor] = useState(false);
  const [enhancementOptions, setEnhancementOptions] = useState<EnhancementOptions>(defaultEnhancementOptions);
  const [maskEditor, setMaskEditor] = useState<MaskEditor | null>(null);
  const [brushSettings, setBrushSettings] = useState<BrushSettings>(defaultBrushSettings);
  const [currentTool, setCurrentTool] = useState<'erase' | 'restore'>('erase');
  const [showGuide, setShowGuide] = useState(true);
  const [guideOpacity, setGuideOpacity] = useState(50);
  const [backgroundColor, setBackgroundColor] = useState<string>('#ffffff');
  const [backgroundImage, setBackgroundImage] = useState<File | null>(null);
  const [backgroundType, setBackgroundType] = useState<'color' | 'image'>('color');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const backgroundImageInputRef = useRef<HTMLInputElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const maskEditorCanvasRef = useRef<HTMLCanvasElement>(null);

  // Predefined colors similar to remove.bg
  const predefinedColors = [
    '#ffffff', // White
    '#000000', // Black
    '#ff0000', // Red
    '#00ff00', // Green
    '#0000ff', // Blue
    '#ffff00', // Yellow
    '#ff00ff', // Magenta
    '#00ffff', // Cyan
    '#ffa500', // Orange
    '#800080', // Purple
    '#ffc0cb', // Pink
    '#a52a2a', // Brown
    '#808080', // Gray
    '#f5f5dc', // Beige
    '#e6e6fa', // Lavender
    '#98fb98', // Pale Green
  ];

  useEffect(() => {
    (async () => {
      try {
        const initialized = await initializeModel();
        if (!initialized) {
          throw new Error("Failed to initialize background removal model");
        }
      } catch (err) {
        console.error(err);
      }
      setIsLoading(false);
    })();
  }, []);

  // Initialize mask editor when modal opens
  useEffect(() => {
    if (showMaskEditor && image?.maskFile && maskEditorCanvasRef.current) {
      initializeMaskEditor(image.maskFile, image.file);
    }
  }, [showMaskEditor, image?.maskFile]);

  // Update mask editor tools when they change
  useEffect(() => {
    if (maskEditor) {
      maskEditor.setTool(currentTool);
      maskEditor.setBrushSettings(brushSettings);
      maskEditor.setShowGuide(showGuide);
      maskEditor.setGuideOpacity(guideOpacity / 100);
    }
  }, [maskEditor, currentTool, brushSettings, showGuide, guideOpacity]);

  const handleImageUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      const newImage = {
        id: Date.now(),
        file: event.target.files[0],
        processedFile: undefined,
      };
      setImage(newImage);
    }
  };

  const handleClick = async (image: {
    id: number;
    file: File;
    processedFile?: File;
    enhancedFile?: File;
  }) => {
    setIsProcessing(true);
    try {
      const result = await processImage(image.file);
      if (result) {
        const { maskFile, processedFile } = result;
        setImage({ ...image, processedFile, maskFile });
      }
    } catch (error) {
      console.error("Error processing image:", error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleEnhanceImage = async (targetFile: File) => {
    setIsEnhancing(true);
    try {
      const enhancedFile = await enhanceImage(targetFile, enhancementOptions);
      if (image) {
        setImage({ ...image, enhancedFile });
      }
    } catch (error) {
      console.error("Error enhancing image:", error);
    } finally {
      setIsEnhancing(false);
    }
  };

  const handleAutoEnhance = async (targetFile: File) => {
    setIsEnhancing(true);
    try {
      const enhancedFile = await autoEnhanceImage(targetFile);
      if (image) {
        setImage({ ...image, enhancedFile });
      }
    } catch (error) {
      console.error("Error auto-enhancing image:", error);
    } finally {
      setIsEnhancing(false);
    }
  };

  const initializeMaskEditor = async (maskFile: File, originalFile: File) => {
    if (!maskEditorCanvasRef.current) return;

    try {
      // Load mask image
      const maskImg = new Image();
      const originalImg = new Image();
      
      // Set crossOrigin to handle CORS if needed
      maskImg.crossOrigin = 'anonymous';
      originalImg.crossOrigin = 'anonymous';
      
      const maskPromise = new Promise<void>((resolve, reject) => {
        maskImg.onload = () => resolve();
        maskImg.onerror = reject;
        maskImg.src = URL.createObjectURL(maskFile);
      });
      
      const originalPromise = new Promise<void>((resolve, reject) => {
        originalImg.onload = () => resolve();
        originalImg.onerror = reject;
        originalImg.src = URL.createObjectURL(originalFile);
      });

      await Promise.all([maskPromise, originalPromise]);

      // Ensure both images have the same dimensions
      const width = Math.min(maskImg.width, originalImg.width);
      const height = Math.min(maskImg.height, originalImg.height);

      // Create temporary canvases to get image data
      const maskCanvas = document.createElement('canvas');
      const originalCanvas = document.createElement('canvas');
      
      maskCanvas.width = width;
      maskCanvas.height = height;
      originalCanvas.width = width;
      originalCanvas.height = height;

      const maskCtx = maskCanvas.getContext('2d');
      const originalCtx = originalCanvas.getContext('2d');

      if (!maskCtx || !originalCtx) {
        throw new Error('Could not get canvas contexts');
      }

      // Draw images to canvases
      maskCtx.drawImage(maskImg, 0, 0, width, height);
      originalCtx.drawImage(originalImg, 0, 0, width, height);

      const maskImageData = maskCtx.getImageData(0, 0, width, height);
      const originalImageData = originalCtx.getImageData(0, 0, width, height);

      // Clean up blob URLs
      URL.revokeObjectURL(maskImg.src);
      URL.revokeObjectURL(originalImg.src);

      // Initialize mask editor
      const editor = new MaskEditor(maskEditorCanvasRef.current, maskImageData, originalImageData);
      editor.setTool(currentTool);
      editor.setBrushSettings(brushSettings);
      editor.setShowGuide(showGuide);
      editor.setGuideOpacity(guideOpacity / 100);
      setMaskEditor(editor);

    } catch (error) {
      console.error('Error initializing mask editor:', error);
      alert('Failed to load images for mask editing. Please try again.');
    }
  };

  const handleMaskEditorMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!maskEditor || !maskEditorCanvasRef.current) return;
    
    const rect = maskEditorCanvasRef.current.getBoundingClientRect();
    const scaleX = maskEditorCanvasRef.current.width / rect.width;
    const scaleY = maskEditorCanvasRef.current.height / rect.height;
    
    const x = (e.clientX - rect.left) * scaleX;
    const y = (e.clientY - rect.top) * scaleY;
    
    maskEditor.startDrawing({ x, y });
  };

  const handleMaskEditorMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!maskEditor || !maskEditorCanvasRef.current) return;
    
    const rect = maskEditorCanvasRef.current.getBoundingClientRect();
    const scaleX = maskEditorCanvasRef.current.width / rect.width;
    const scaleY = maskEditorCanvasRef.current.height / rect.height;
    
    const x = (e.clientX - rect.left) * scaleX;
    const y = (e.clientY - rect.top) * scaleY;
    
    // Continue drawing if mouse is down (this will update display if drawing)
    const wasDrawing = maskEditor.isDrawing;
    maskEditor.continueDrawing({ x, y });
    
    // If not drawing, just show cursor preview
    if (!wasDrawing) {
      maskEditor.updateDisplay();
      maskEditor.drawCursorPreview(x, y);
    }
  };

  const handleMaskEditorMouseUp = () => {
    if (!maskEditor) return;
    maskEditor.stopDrawing();
  };

  const handleMaskEditorMouseLeave = () => {
    if (!maskEditor) return;
    maskEditor.stopDrawing();
    maskEditor.updateDisplay(); // Clear cursor preview
  };

  const applyMaskEditorChanges = async () => {
    if (!maskEditor || !image) return;

    try {
      const newMaskFile = await maskEditor.getMaskAsFile(image.file.name);
      const newProcessedFile = await maskEditor.getProcessedImageAsFile(image.file.name);
      
      setImage({
        ...image,
        maskFile: newMaskFile,
        processedFile: newProcessedFile
      });
      
      setShowMaskEditor(false);
    } catch (error) {
      console.error('Error applying mask editor changes:', error);
    }
  };

  const closeMaskEditor = () => {
    if (maskEditor) {
      maskEditor.cleanup();
      setMaskEditor(null);
    }
    setShowMaskEditor(false);
    // Reset tool state
    setCurrentTool('erase');
    setBrushSettings(defaultBrushSettings);
    setShowGuide(true);
    setGuideOpacity(50);
  };

  const createImageWithBackground = (imageFile: File, bgColor?: string, bgImage?: File): Promise<File> => {
    return new Promise((resolve) => {
      const canvas = canvasRef.current!;
      const ctx = canvas.getContext('2d')!;
      const img = new Image();
      
      img.onload = () => {
        canvas.width = img.width;
        canvas.height = img.height;
        
        if (bgImage) {
          // Use background image
          const bgImg = new Image();
          bgImg.onload = () => {
            // Draw background image (scaled to fit)
            ctx.drawImage(bgImg, 0, 0, canvas.width, canvas.height);
            // Draw foreground image on top
            ctx.drawImage(img, 0, 0);
            
            canvas.toBlob((blob) => {
              const file = new File([blob!], `photofix-with-bg-image-${Date.now()}.png`, {
                type: 'image/png'
              });
              resolve(file);
            }, 'image/png');
          };
          bgImg.src = URL.createObjectURL(bgImage);
        } else {
          // Use background color
          ctx.fillStyle = bgColor || '#ffffff';
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          
          // Draw image on top
          ctx.drawImage(img, 0, 0);
          
          canvas.toBlob((blob) => {
            const file = new File([blob!], `photofix-with-bg-${Date.now()}.png`, {
              type: 'image/png'
            });
            resolve(file);
          }, 'image/png');
        }
      };
      
      img.src = URL.createObjectURL(imageFile);
    });
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    const files = e.dataTransfer.files;
    if (files && files[0] && files[0].type.startsWith('image/')) {
      const newImage = {
        id: Date.now(),
        file: files[0],
        processedFile: undefined,
      };
      setImage(newImage);
    }
  };

  const downloadImage = (file: File, filename: string) => {
    const url = URL.createObjectURL(file);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const downloadWithBackground = async () => {
    if (image?.processedFile) {
      if (backgroundType === 'image' && backgroundImage) {
        const imageWithBg = await createImageWithBackground(image.processedFile, undefined, backgroundImage);
        downloadImage(imageWithBg, `photofix-with-background-image-${Date.now()}.png`);
      } else {
        const imageWithBg = await createImageWithBackground(image.processedFile, backgroundColor);
        downloadImage(imageWithBg, `photofix-with-background-${Date.now()}.png`);
      }
    }
  };

  const handleBackgroundImageUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setBackgroundImage(event.target.files[0]);
      setBackgroundType('image');
    }
  };

  const removeBackgroundImage = () => {
    setBackgroundImage(null);
    setBackgroundType('color');
    if (backgroundImageInputRef.current) {
      backgroundImageInputRef.current.value = '';
    }
  };

  const resetApp = () => {
    setImage(null);
    setBackgroundColor('#ffffff');
    setBackgroundImage(null);
    setBackgroundType('color');
    setShowEnhancementControls(false);
    setShowMaskEditor(false);
    setEnhancementOptions(defaultEnhancementOptions);
    if (maskEditor) {
      maskEditor.cleanup();
      setMaskEditor(null);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    if (backgroundImageInputRef.current) {
      backgroundImageInputRef.current.value = '';
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center px-4">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent mb-6"></div>
          <h2 className="text-2xl font-semibold text-gray-800 mb-2">Loading AI model...</h2>
          <p className="text-gray-600">This may take a moment</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Header - Remove.bg style */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">PF</span>
              </div>
              <h1 className="text-2xl font-bold text-gray-900">PhotoFix</h1>
            </div>
            {image && (
              <button
                onClick={resetApp}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-500 hover:bg-blue-600 transition-colors shadow-sm"
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
                Upload new image
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {!image ? (
          /* Upload Section - Remove.bg style */
          <div className="text-center">
            <div className="mb-8">
              <h2 className="text-4xl font-bold text-gray-900 mb-4">
                Remove Background & Enhance Images
              </h2>
              <p className="text-xl text-gray-600 max-w-2xl mx-auto">
                100% automatically remove backgrounds and enhance image quality – remove blemishes, reduce noise, and improve clarity in seconds
              </p>
            </div>
            
            <div 
              className="mx-auto max-w-2xl border-2 border-dashed border-blue-300 rounded-lg p-16 hover:border-blue-400 transition-colors cursor-pointer bg-blue-50/50"
              onDragOver={handleDragOver}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <div className="text-center">
                <svg className="mx-auto h-16 w-16 text-blue-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">Upload image</h3>
                <p className="text-gray-600 mb-6">or drop a file</p>
                <button className="inline-flex items-center px-8 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-500 hover:bg-blue-600 transition-colors">
                  Select a photo
                </button>
              </div>
            </div>
            
            <div className="mt-8 text-sm text-gray-500">
              <p>Paste image or URL (Ctrl+V)</p>
            </div>
            
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleImageUpload}
              className="hidden"
            />
          </div>
        ) : (
          /* Processing Section */
          <div className="space-y-8">
            {/* Image Display */}
            <div className="grid md:grid-cols-3 gap-6">
              {/* Original */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-900">Original</h3>
                <div className="bg-gray-100 rounded-lg overflow-hidden">
                  <img 
                    src={URL.createObjectURL(image.file)} 
                    alt="Original" 
                    className="w-full h-auto"
                  />
                </div>
                <div className="space-y-2">
                  <button
                    onClick={() => handleAutoEnhance(image.file)}
                    disabled={isEnhancing}
                    className="w-full inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-purple-500 hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {isEnhancing ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2"></div>
                        Enhancing...
                      </>
                    ) : (
                      <>
                        <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        Auto Enhance
                      </>
                    )}
                  </button>
                  <button
                    onClick={() => setShowEnhancementControls(!showEnhancementControls)}
                    className="w-full inline-flex items-center justify-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors"
                  >
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4" />
                    </svg>
                    Manual Enhance
                  </button>
                </div>
              </div>
              
              {/* Enhanced */}
              {image.enhancedFile && (
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-gray-900">Enhanced</h3>
                  <div className="bg-gray-100 rounded-lg overflow-hidden">
                    <img 
                      src={URL.createObjectURL(image.enhancedFile)} 
                      alt="Enhanced" 
                      className="w-full h-auto"
                    />
                  </div>
                  <div className="space-y-2">
                    <button
                      onClick={() => downloadImage(image.enhancedFile!, `enhanced-${Date.now()}.png`)}
                      className="w-full inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-500 hover:bg-green-600 transition-colors"
                    >
                      <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      Download Enhanced
                    </button>
                    {!image.processedFile && (
                      <button
                        onClick={() => handleClick({ ...image, file: image.enhancedFile! })}
                        disabled={isProcessing}
                        className="w-full inline-flex items-center justify-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        Remove Background
                      </button>
                    )}
                  </div>
                </div>
              )}
              
              {/* Background Removed */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-900">
                  {image.processedFile ? 'Background removed' : 'Preview'}
                </h3>
                <div className="bg-gray-100 rounded-lg overflow-hidden relative">
                  {image.processedFile ? (
                    <div 
                      className="relative"
                      style={{ 
                        background: backgroundType === 'image' && backgroundImage
                          ? `url(${URL.createObjectURL(backgroundImage)}) center/cover`
                          : backgroundColor === 'transparent' 
                            ? 'linear-gradient(45deg, #f0f0f0 25%, transparent 25%), linear-gradient(-45deg, #f0f0f0 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #f0f0f0 75%), linear-gradient(-45deg, transparent 75%, #f0f0f0 75%)'
                            : backgroundColor,
                        backgroundSize: backgroundColor === 'transparent' ? '20px 20px' : 'cover',
                        backgroundPosition: backgroundColor === 'transparent' ? '0 0, 0 10px, 10px -10px, -10px 0px' : 'center',
                        backgroundRepeat: 'no-repeat'
                      }}
                    >
                      <img 
                        src={URL.createObjectURL(image.processedFile)} 
                        alt="Background Removed" 
                        className="w-full h-auto"
                      />
                    </div>
                  ) : (
                    <div className="aspect-video flex items-center justify-center text-gray-400">
                      {isProcessing ? (
                        <div className="text-center">
                          <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-500 border-t-transparent mx-auto mb-4"></div>
                          <p>Processing...</p>
                        </div>
                      ) : (
                        <p>Click process to remove background</p>
                      )}
                    </div>
                  )}
                </div>
                {image.processedFile && (
                  <div className="space-y-2">
                    <button
                      onClick={() => downloadImage(image.processedFile!, `background-removed-${Date.now()}.png`)}
                      className="w-full inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-500 hover:bg-green-600 transition-colors"
                    >
                      <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      Download
                    </button>
                    {image.maskFile && (
                      <button
                        onClick={() => {
                          setShowMaskEditor(true);
                        }}
                        className="w-full inline-flex items-center justify-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors"
                      >
                        <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                        </svg>
                        Edit Mask
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Enhancement Controls */}
            {showEnhancementControls && (
              <div className="bg-white border border-gray-200 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Manual Enhancement Controls</h3>
                
                <div className="grid md:grid-cols-2 gap-6">
                  {/* Basic Enhancements */}
                  <div className="space-y-4">
                    <h4 className="font-medium text-gray-800">Basic Enhancements</h4>
                    
                    <div className="space-y-3">
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={enhancementOptions.blemishRemoval}
                          onChange={(e) => setEnhancementOptions({...enhancementOptions, blemishRemoval: e.target.checked})}
                          className="rounded border-gray-300 text-purple-500 focus:ring-purple-500"
                        />
                        <span className="ml-2 text-sm text-gray-700">Remove Blemishes</span>
                      </label>
                      
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={enhancementOptions.noiseReduction}
                          onChange={(e) => setEnhancementOptions({...enhancementOptions, noiseReduction: e.target.checked})}
                          className="rounded border-gray-300 text-purple-500 focus:ring-purple-500"
                        />
                        <span className="ml-2 text-sm text-gray-700">Reduce Noise/Grain</span>
                      </label>
                      
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={enhancementOptions.sharpen}
                          onChange={(e) => setEnhancementOptions({...enhancementOptions, sharpen: e.target.checked})}
                          className="rounded border-gray-300 text-purple-500 focus:ring-purple-500"
                        />
                        <span className="ml-2 text-sm text-gray-700">Sharpen Image</span>
                      </label>
                    </div>
                  </div>
                  
                  {/* Advanced Adjustments */}
                  <div className="space-y-4">
                    <h4 className="font-medium text-gray-800">Advanced Adjustments</h4>
                    
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Brightness: {enhancementOptions.brightnessAdjust}
                        </label>
                        <input
                          type="range"
                          min="-100"
                          max="100"
                          value={enhancementOptions.brightnessAdjust}
                          onChange={(e) => setEnhancementOptions({...enhancementOptions, brightnessAdjust: parseInt(e.target.value)})}
                          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                        />
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Contrast: {enhancementOptions.contrastAdjust}
                        </label>
                        <input
                          type="range"
                          min="-100"
                          max="100"
                          value={enhancementOptions.contrastAdjust}
                          onChange={(e) => setEnhancementOptions({...enhancementOptions, contrastAdjust: parseInt(e.target.value)})}
                          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                        />
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Saturation: {enhancementOptions.saturationAdjust}
                        </label>
                        <input
                          type="range"
                          min="-100"
                          max="100"
                          value={enhancementOptions.saturationAdjust}
                          onChange={(e) => setEnhancementOptions({...enhancementOptions, saturationAdjust: parseInt(e.target.value)})}
                          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                        />
                      </div>
                    </div>
                  </div>
                </div>
                
                <div className="mt-6 flex justify-center space-x-4">
                  <button
                    onClick={() => setEnhancementOptions(defaultEnhancementOptions)}
                    className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors"
                  >
                    Reset to Default
                  </button>
                  <button
                    onClick={() => handleEnhanceImage(image.file)}
                    disabled={isEnhancing}
                    className="px-6 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-purple-500 hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {isEnhancing ? 'Enhancing...' : 'Apply Enhancement'}
                  </button>
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex flex-wrap justify-center gap-4">
              {!image.processedFile ? (
                <button
                  onClick={() => handleClick(image)}
                  disabled={isProcessing}
                  className="inline-flex items-center px-8 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-500 hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isProcessing ? (
                    <>
                      <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent mr-3"></div>
                      Processing...
                    </>
                  ) : (
                    <>
                      <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                      Remove Background
                    </>
                  )}
                </button>
              ) : (
                <div className="flex flex-wrap gap-4">
                  <button
                    onClick={() => downloadImage(image.processedFile!, `photofix-${Date.now()}.png`)}
                    className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-green-500 hover:bg-green-600 transition-colors"
                  >
                    <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Download
                  </button>
                  {(backgroundColor !== 'transparent' || backgroundImage) && (
                    <button
                      onClick={downloadWithBackground}
                      className="inline-flex items-center px-6 py-3 border border-gray-300 rounded-md shadow-sm text-base font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors"
                    >
                      <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                      Download with background
                    </button>
                  )}
                  {image.enhancedFile && (
                    <button
                      onClick={() => handleEnhanceImage(image.processedFile!)}
                      disabled={isEnhancing}
                      className="inline-flex items-center px-6 py-3 border border-purple-300 rounded-md shadow-sm text-base font-medium text-purple-700 bg-white hover:bg-purple-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {isEnhancing ? (
                        <>
                          <div className="animate-spin rounded-full h-5 w-5 border-2 border-purple-500 border-t-transparent mr-2"></div>
                          Enhancing...
                        </>
                      ) : (
                        <>
                          <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                          </svg>
                          Enhance Result
                        </>
                      )}
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Background Selection */}
            {image.processedFile && (
              <div className="bg-white border border-gray-200 rounded-lg p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Background</h3>
                
                {/* Background Type Selector */}
                <div className="flex gap-4 mb-6">
                  <button
                    onClick={() => setBackgroundType('color')}
                    className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                      backgroundType === 'color'
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    Solid Color
                  </button>
                  <button
                    onClick={() => setBackgroundType('image')}
                    className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                      backgroundType === 'image'
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    Custom Image
                  </button>
                </div>

                {backgroundType === 'color' ? (
                  <>
                    {/* Predefined Colors */}
                    <div className="grid grid-cols-8 gap-3 mb-4">
                      <button
                        onClick={() => setBackgroundColor('transparent')}
                        className={`w-12 h-12 rounded border-2 ${backgroundColor === 'transparent' ? 'border-blue-500' : 'border-gray-300'} relative overflow-hidden`}
                        title="Transparent"
                      >
                        <div 
                          className="w-full h-full"
                          style={{ 
                            background: 'linear-gradient(45deg, #f0f0f0 25%, transparent 25%), linear-gradient(-45deg, #f0f0f0 25%, transparent 25%), linear-gradient(45deg, transparent 75%, #f0f0f0 75%), linear-gradient(-45deg, transparent 75%, #f0f0f0 75%)',
                            backgroundSize: '8px 8px',
                            backgroundPosition: '0 0, 0 4px, 4px -4px, -4px 0px'
                          }}
                        />
                      </button>
                      {predefinedColors.map((color) => (
                        <button
                          key={color}
                          onClick={() => setBackgroundColor(color)}
                          className={`w-12 h-12 rounded border-2 ${backgroundColor === color ? 'border-blue-500' : 'border-gray-300'}`}
                          style={{ backgroundColor: color }}
                          title={color}
                        />
                      ))}
                    </div>
                    
                    {/* Custom Color Picker */}
                    <div className="flex items-center gap-4">
                      <label className="text-sm font-medium text-gray-700">Custom color:</label>
                      <input
                        type="color"
                        value={backgroundColor === 'transparent' ? '#ffffff' : backgroundColor}
                        onChange={(e) => setBackgroundColor(e.target.value)}
                        className="w-12 h-8 rounded border border-gray-300 cursor-pointer"
                      />
                      <input
                        type="text"
                        value={backgroundColor}
                        onChange={(e) => setBackgroundColor(e.target.value)}
                        className="px-3 py-1 border border-gray-300 rounded text-sm font-mono"
                        placeholder="#ffffff"
                      />
                    </div>
                  </>
                ) : (
                  <>
                    {/* Background Image Upload */}
                    <div className="space-y-4">
                      {!backgroundImage ? (
                        <div 
                          className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-blue-400 transition-colors"
                          onClick={() => backgroundImageInputRef.current?.click()}
                        >
                          <svg className="mx-auto h-12 w-12 text-gray-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                          </svg>
                          <p className="text-gray-600 font-medium">Upload background image</p>
                          <p className="text-sm text-gray-500 mt-1">Click to browse files</p>
                        </div>
                      ) : (
                        <div className="relative">
                          <img 
                            src={URL.createObjectURL(backgroundImage)} 
                            alt="Background" 
                            className="w-full h-32 object-cover rounded-lg"
                          />
                          <button
                            onClick={removeBackgroundImage}
                            className="absolute top-2 right-2 p-1 bg-red-500 text-white rounded-full hover:bg-red-600 transition-colors"
                            title="Remove background image"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        </div>
                      )}
                      <input
                        ref={backgroundImageInputRef}
                        type="file"
                        accept="image/*"
                        onChange={handleBackgroundImageUpload}
                        className="hidden"
                      />
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        )}
      </main>
      
      {/* Mask Editor Modal */}
      {showMaskEditor && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 overflow-y-auto">
          <div className="bg-white rounded-lg max-w-6xl w-full my-4 shadow-2xl" style={{ maxHeight: 'calc(100vh - 2rem)' }}>
            <div className="sticky top-0 bg-white border-b border-gray-200 p-4 rounded-t-lg z-10">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold text-gray-900">Edit Mask - Fix Background Removal</h2>
                <button
                  onClick={closeMaskEditor}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              {/* Tool Controls */}
              <div className="mt-4 space-y-4">
                <div className="flex items-center space-x-4">
                  <div className="flex space-x-2">
                    <button
                      onClick={() => {
                        setCurrentTool('erase');
                        if (maskEditor) maskEditor.setTool('erase');
                      }}
                      className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                        currentTool === 'erase'
                          ? 'bg-red-500 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      <svg className="w-4 h-4 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                      Erase
                    </button>
                    <button
                      onClick={() => {
                        setCurrentTool('restore');
                        if (maskEditor) maskEditor.setTool('restore');
                      }}
                      className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                        currentTool === 'restore'
                          ? 'bg-green-500 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      <svg className="w-4 h-4 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                      </svg>
                      Restore
                    </button>
                  </div>
                  
                  <div className="flex items-center space-x-4">
                    <div className="flex items-center space-x-2">
                      <label className="text-sm font-medium text-gray-700">Size:</label>
                      <input
                        type="range"
                        min="5"
                        max="100"
                        value={brushSettings.size}
                        onChange={(e) => {
                          const newSettings = { ...brushSettings, size: parseInt(e.target.value) };
                          setBrushSettings(newSettings);
                          if (maskEditor) maskEditor.setBrushSettings(newSettings);
                        }}
                        className="w-20"
                      />
                      <span className="text-sm text-gray-600 w-8">{brushSettings.size}</span>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      <label className="text-sm font-medium text-gray-700">Hardness:</label>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={brushSettings.hardness * 100}
                        onChange={(e) => {
                          const newSettings = { ...brushSettings, hardness: parseInt(e.target.value) / 100 };
                          setBrushSettings(newSettings);
                          if (maskEditor) maskEditor.setBrushSettings(newSettings);
                        }}
                        className="w-20"
                      />
                      <span className="text-sm text-gray-600 w-8">{Math.round(brushSettings.hardness * 100)}</span>
                    </div>
                  </div>
                </div>
                
                {/* Guide Controls */}
                <div className="flex items-center justify-between p-4 bg-blue-50 rounded-lg">
                  <div className="flex items-center space-x-4">
                    <label className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        checked={showGuide}
                        onChange={(e) => {
                          setShowGuide(e.target.checked);
                          if (maskEditor) maskEditor.setShowGuide(e.target.checked);
                        }}
                        className="rounded border-gray-300 text-blue-500 focus:ring-blue-500"
                      />
                      <span className="text-sm font-medium text-gray-700">Show Original Guide</span>
                    </label>
                    
                    {showGuide && (
                      <div className="flex items-center space-x-2">
                        <label className="text-sm font-medium text-gray-700">Opacity:</label>
                        <input
                          type="range"
                          min="10"
                          max="80"
                          value={guideOpacity}
                          onChange={(e) => {
                            const opacity = parseInt(e.target.value);
                            setGuideOpacity(opacity);
                            if (maskEditor) maskEditor.setGuideOpacity(opacity / 100);
                          }}
                          className="w-20"
                        />
                        <span className="text-sm text-gray-600 w-8">{guideOpacity}%</span>
                      </div>
                    )}
                  </div>
                  
                  <div className="text-xs text-blue-700">
                    <p>💡 The guide shows the original image to help you see what to restore or erase</p>
                  </div>
                </div>
                
                <div className="text-sm text-gray-600">
                  <p><strong>Erase:</strong> Remove parts that should be transparent (like incorrectly kept background)</p>
                  <p><strong>Restore:</strong> Bring back parts that should be kept (like shoulders or other body parts)</p>
                </div>
              </div>
            </div>
            
            <div className="p-4 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 200px)' }}>
              <div className="flex justify-center mb-4">
                <div className="relative inline-block">
                  <canvas
                    ref={maskEditorCanvasRef}
                    onMouseDown={handleMaskEditorMouseDown}
                    onMouseMove={handleMaskEditorMouseMove}
                    onMouseUp={handleMaskEditorMouseUp}
                    onMouseLeave={handleMaskEditorMouseLeave}
                    className="border-2 border-gray-300 rounded cursor-crosshair shadow-lg block"
                    style={{ 
                      cursor: currentTool === 'erase' ? 'crosshair' : 'copy',
                      maxWidth: '100%',
                      height: 'auto',
                      backgroundColor: '#f9fafb'
                    }}
                  />
                  {!maskEditor && (
                    <div className="absolute inset-0 flex items-center justify-center bg-gray-100 rounded">
                      <div className="text-center">
                        <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-500 border-t-transparent mx-auto mb-2"></div>
                        <p className="text-gray-600">Loading mask editor...</p>
                      </div>
                    </div>
                  )}
                  {showGuide && maskEditor && (
                    <div className="absolute top-2 left-2 bg-blue-500 text-white px-2 py-1 rounded text-xs font-medium shadow">
                      Guide: {guideOpacity}%
                    </div>
                  )}
                </div>
              </div>
              
              <div className="text-center text-sm text-gray-600 mb-4">
                <p>Click and drag to edit the mask. The <strong className="text-blue-500">original image guide</strong> helps you see what should be kept or removed.</p>
                <p>Use <strong className="text-red-500">Erase</strong> to remove unwanted areas, <strong className="text-green-500">Restore</strong> to bring back removed parts.</p>
              </div>
              
              <div className="mt-6 flex justify-center space-x-4 border-t pt-4">
                <button
                  onClick={closeMaskEditor}
                  className="px-6 py-2 border border-gray-300 rounded-md shadow-sm text-base font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={applyMaskEditorChanges}
                  className="px-6 py-2 border border-transparent rounded-md shadow-sm text-base font-medium text-white bg-blue-500 hover:bg-blue-600 transition-colors"
                >
                  Apply Changes
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Hidden canvas for background composition */}
      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
}
