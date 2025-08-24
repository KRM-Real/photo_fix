import React, { useEffect, useState, useRef } from "react";
import { initializeModel, processImage } from "./lib/process";

export default function App() {
  const [image, setImage] = useState<{
    id: number;
    file: File;
    maskFile?: File;
    processedFile?: File;
  } | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [backgroundColor, setBackgroundColor] = useState<string>('#ffffff');
  const [backgroundImage, setBackgroundImage] = useState<File | null>(null);
  const [backgroundType, setBackgroundType] = useState<'color' | 'image'>('color');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const backgroundImageInputRef = useRef<HTMLInputElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

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
                Remove Image Background
              </h2>
              <p className="text-xl text-gray-600 max-w-2xl mx-auto">
                100% automatically – in 5 seconds – without a single click
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
            <div className="grid md:grid-cols-2 gap-8">
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
              </div>
              
              {/* Result */}
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
              </div>
            </div>

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
                    'Remove Background'
                  )}
                </button>
              ) : (
                <div className="flex flex-wrap gap-4">
                  <button
                    onClick={() => downloadImage(image.processedFile!, `photofix-${Date.now()}.png`)}
                    className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-green-500 hover:bg-green-600 transition-colors"
                  >
                    Download
                  </button>
                  {(backgroundColor !== 'transparent' || backgroundImage) && (
                    <button
                      onClick={downloadWithBackground}
                      className="inline-flex items-center px-6 py-3 border border-gray-300 rounded-md shadow-sm text-base font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors"
                    >
                      Download with background
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
      
      {/* Hidden canvas for background composition */}
      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
}
