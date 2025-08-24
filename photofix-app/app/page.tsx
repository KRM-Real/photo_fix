"use client"

import type React from "react"

import { useState, useRef, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import { Upload, Scissors, Palette, Shirt, Sparkles, Download, ImageIcon, Check } from "lucide-react"

export default function PhotoFixApp() {
  const [uploadedImage, setUploadedImage] = useState<string | null>(null)
  const [processedImage, setProcessedImage] = useState<string | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [activeTab, setActiveTab] = useState("upload")
  const [selectedBackground, setSelectedBackground] = useState("#ffffff")
  const [selectedAttire, setSelectedAttire] = useState("")
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileUpload = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      const reader = new FileReader()
      reader.onload = (e) => {
        setUploadedImage(e.target?.result as string)
        setActiveTab("edit")
      }
      reader.readAsDataURL(file)
    }
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file && file.type.startsWith("image/")) {
      const reader = new FileReader()
      reader.onload = (e) => {
        setUploadedImage(e.target?.result as string)
        setActiveTab("edit")
      }
      reader.readAsDataURL(file)
    }
  }, [])

  const simulateProcessing = useCallback(
    (action: string) => {
      setIsProcessing(true)
      setProgress(0)

      const interval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 100) {
            clearInterval(interval)
            setIsProcessing(false)
            setProcessedImage(uploadedImage) // In real app, this would be the processed result
            return 100
          }
          return prev + 10
        })
      }, 200)
    },
    [uploadedImage],
  )

  const backgroundColors = [
    { name: "White", value: "#ffffff" },
    { name: "Light Blue", value: "#dbeafe" },
    { name: "Light Gray", value: "#f3f4f6" },
    { name: "Red", value: "#fecaca" },
  ]

  const attireOptions = [
    { name: "Navy Blazer", preview: "/navy-blazer-formal-wear.png" },
    { name: "White Shirt", preview: "/white-dress-shirt-formal.png" },
    { name: "Black Suit", preview: "/black-business-suit-formal.png" },
  ]

  return (
    <div className="min-h-screen bg-background font-sans">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <ImageIcon className="w-5 h-5 text-primary-foreground" />
            </div>
            <h1 className="text-2xl font-bold text-foreground">PhotoFix</h1>
            <span className="text-sm text-muted-foreground">Professional ID Photo Editor</span>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-6 py-8">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-2 mb-8">
            <TabsTrigger value="upload" className="font-medium">
              Upload Photo
            </TabsTrigger>
            <TabsTrigger value="edit" disabled={!uploadedImage} className="font-medium">
              Edit & Enhance
            </TabsTrigger>
          </TabsList>

          <TabsContent value="upload" className="space-y-6">
            <Card className="border-2 border-dashed border-border hover:border-primary/50 transition-colors">
              <CardContent className="p-12">
                <div
                  className="text-center space-y-4 cursor-pointer"
                  onDragOver={handleDragOver}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto">
                    <Upload className="w-8 h-8 text-muted-foreground" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-foreground mb-2">Upload Your Photo</h3>
                    <p className="text-muted-foreground mb-4">Drag and drop your image here, or click to browse</p>
                    <p className="text-sm text-muted-foreground">Supports JPG, PNG files up to 10MB</p>
                  </div>
                  <Button variant="outline" className="mt-4 bg-transparent">
                    Choose File
                  </Button>
                </div>
                <input ref={fileInputRef} type="file" accept="image/*" onChange={handleFileUpload} className="hidden" />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="edit" className="space-y-6">
            <div className="grid lg:grid-cols-3 gap-6">
              {/* Tools Sidebar */}
              <div className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg font-semibold">Editing Tools</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <Button
                      variant="outline"
                      className="w-full justify-start gap-3 h-12 bg-transparent"
                      onClick={() => simulateProcessing("remove-background")}
                      disabled={isProcessing}
                    >
                      <Scissors className="w-5 h-5" />
                      Remove Background
                    </Button>

                    <div className="space-y-3">
                      <Button
                        variant="outline"
                        className="w-full justify-start gap-3 h-12 bg-transparent"
                        onClick={() => simulateProcessing("change-background")}
                        disabled={isProcessing}
                      >
                        <Palette className="w-5 h-5" />
                        Change Background
                      </Button>

                      <div className="grid grid-cols-4 gap-2 px-3">
                        {backgroundColors.map((color) => (
                          <button
                            key={color.value}
                            className={`w-8 h-8 rounded-full border-2 ${
                              selectedBackground === color.value ? "border-primary" : "border-border"
                            }`}
                            style={{ backgroundColor: color.value }}
                            onClick={() => setSelectedBackground(color.value)}
                            title={color.name}
                          />
                        ))}
                      </div>
                    </div>

                    <div className="space-y-3">
                      <Button
                        variant="outline"
                        className="w-full justify-start gap-3 h-12 bg-transparent"
                        onClick={() => simulateProcessing("change-attire")}
                        disabled={isProcessing}
                      >
                        <Shirt className="w-5 h-5" />
                        Formal Attire
                      </Button>

                      <div className="grid grid-cols-3 gap-2 px-3">
                        {attireOptions.map((attire) => (
                          <button
                            key={attire.name}
                            className={`aspect-square rounded-lg border-2 overflow-hidden ${
                              selectedAttire === attire.name ? "border-primary" : "border-border"
                            }`}
                            onClick={() => setSelectedAttire(attire.name)}
                            title={attire.name}
                          >
                            <img
                              src={attire.preview || "/placeholder.svg"}
                              alt={attire.name}
                              className="w-full h-full object-cover"
                            />
                          </button>
                        ))}
                      </div>
                    </div>

                    <Button
                      variant="outline"
                      className="w-full justify-start gap-3 h-12 bg-transparent"
                      onClick={() => simulateProcessing("enhance")}
                      disabled={isProcessing}
                    >
                      <Sparkles className="w-5 h-5" />
                      Enhance Picture
                    </Button>
                  </CardContent>
                </Card>

                {/* Export Options */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg font-semibold">Export Options</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <Button className="w-full gap-2" disabled={!processedImage}>
                      <Download className="w-4 h-4" />
                      Download PNG
                    </Button>
                    <Button variant="outline" className="w-full gap-2 bg-transparent" disabled={!processedImage}>
                      <Download className="w-4 h-4" />
                      Download JPG
                    </Button>
                    <div className="pt-2 border-t border-border">
                      <p className="text-sm text-muted-foreground mb-2">ID Photo Sizes:</p>
                      <div className="grid grid-cols-2 gap-2">
                        <Button variant="outline" size="sm" disabled={!processedImage}>
                          1x1 inch
                        </Button>
                        <Button variant="outline" size="sm" disabled={!processedImage}>
                          2x2 inch
                        </Button>
                        <Button variant="outline" size="sm" disabled={!processedImage}>
                          35x45mm
                        </Button>
                        <Button variant="outline" size="sm" disabled={!processedImage}>
                          Custom
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Image Preview Area */}
              <div className="lg:col-span-2 space-y-4">
                {isProcessing && (
                  <Card>
                    <CardContent className="p-6">
                      <div className="space-y-3">
                        <div className="flex items-center gap-2">
                          <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                          <span className="text-sm font-medium">Processing your image...</span>
                        </div>
                        <Progress value={progress} className="w-full" />
                      </div>
                    </CardContent>
                  </Card>
                )}

                <div className="grid md:grid-cols-2 gap-4">
                  {/* Original Image */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base font-medium">Original</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="aspect-[3/4] bg-muted rounded-lg overflow-hidden">
                        {uploadedImage ? (
                          <img
                            src={uploadedImage || "/placeholder.svg"}
                            alt="Original"
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            <ImageIcon className="w-12 h-12 text-muted-foreground" />
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>

                  {/* Processed Image */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base font-medium flex items-center gap-2">
                        Enhanced
                        {processedImage && <Check className="w-4 h-4 text-green-500" />}
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="aspect-[3/4] bg-muted rounded-lg overflow-hidden">
                        {processedImage ? (
                          <img
                            src={processedImage || "/placeholder.svg"}
                            alt="Processed"
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            <div className="text-center space-y-2">
                              <ImageIcon className="w-12 h-12 text-muted-foreground mx-auto" />
                              <p className="text-sm text-muted-foreground">Processed image will appear here</p>
                            </div>
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
