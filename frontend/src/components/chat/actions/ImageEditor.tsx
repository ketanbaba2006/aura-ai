"use client";

import { useEffect, useRef, useState } from "react";
import { X, Check, RotateCcw, Paintbrush, Square, Trash2, Undo } from "lucide-react";

interface ImageEditorProps {
  onSave: (file: File) => void;
  onClose: () => void;
}

export function ImageEditor({ onSave, onClose }: ImageEditorProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  
  const [imageSrc, setImageSrc] = useState<string | null>(null);
  const [brushColor, setBrushColor] = useState("#06d6d6"); // neon cyan default
  const [brushWidth, setBrushWidth] = useState(4);
  const [isDrawing, setIsDrawing] = useState(false);
  const [history, setHistory] = useState<ImageData[]>([]);
  const [isImageLoaded, setIsImageLoaded] = useState(false);

  // Neon colors palette
  const neonColors = ["#06d6d6", "#8b5cf6", "#ef4444", "#10b981", "#f59e0b", "#ffffff", "#000000"];

  // File drop handler
  const handleFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      loadImage(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      loadImage(e.target.files[0]);
    }
  };

  const loadImage = (file: File) => {
    const reader = new FileReader();
    reader.onload = (event) => {
      if (event.target?.result) {
        setImageSrc(event.target.result as string);
        setIsImageLoaded(false);
      }
    };
    reader.readAsDataURL(file);
  };

  // Draw background image
  useEffect(() => {
    if (!imageSrc || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const img = new Image();
    img.src = imageSrc;
    img.onload = () => {
      // Find fitting dimensions in editor view
      const maxW = 560;
      const maxH = 280;
      let w = img.width;
      let h = img.height;

      if (w > maxW) {
        h = (maxW / w) * h;
        w = maxW;
      }
      if (h > maxH) {
        w = (maxH / h) * w;
        h = maxH;
      }

      canvas.width = w;
      canvas.height = h;

      ctx.drawImage(img, 0, 0, w, h);
      
      // Save initial canvas state
      const initialData = ctx.getImageData(0, 0, w, h);
      setHistory([initialData]);
      setIsImageLoaded(true);
    };
  }, [imageSrc]);

  // Drawing mouse handlers
  const startDrawing = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.strokeStyle = brushColor;
    ctx.lineWidth = brushWidth;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    setIsDrawing(true);
  };

  const draw = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return;

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    ctx.lineTo(x, y);
    ctx.stroke();
  };

  const stopDrawing = () => {
    if (!isDrawing) return;
    setIsDrawing(false);

    // Save history
    const canvas = canvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext("2d");
      if (ctx) {
        const state = ctx.getImageData(0, 0, canvas.width, canvas.height);
        setHistory((prev) => [...prev, state]);
      }
    }
  };

  // Touch triggers for mobile responsiveness
  const startDrawingTouch = (e: React.TouchEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || e.touches.length === 0) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.touches[0].clientX - rect.left;
    const y = e.touches[0].clientY - rect.top;

    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.strokeStyle = brushColor;
    ctx.lineWidth = brushWidth;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    setIsDrawing(true);
  };

  const drawTouch = (e: React.TouchEvent<HTMLCanvasElement>) => {
    if (!isDrawing || e.touches.length === 0) return;

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.touches[0].clientX - rect.left;
    const y = e.touches[0].clientY - rect.top;

    ctx.lineTo(x, y);
    ctx.stroke();
  };

  const handleUndo = () => {
    if (history.length <= 1) return; // Keep initial state

    const newHistory = history.slice(0, -1);
    setHistory(newHistory);

    const canvas = canvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext("2d");
      if (ctx) {
        ctx.putImageData(newHistory[newHistory.length - 1], 0, 0);
      }
    }
  };

  const handleClear = () => {
    if (!canvasRef.current || !imageSrc) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Reset to base background image
    const img = new Image();
    img.src = imageSrc;
    img.onload = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      const initialData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      setHistory([initialData]);
    };
  };

  const handleConfirm = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    canvas.toBlob((blob) => {
      if (blob) {
        const file = new File([blob], `edited_image_${Date.now()}.png`, {
          type: "image/png",
        });
        onSave(file);
      }
    }, "image/png");
  };

  return (
    <div
      ref={containerRef}
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        width: "100%",
        height: "380px",
        background: "#05050a",
        borderRadius: "14px",
        overflow: "hidden",
        border: "1px solid rgba(255, 255, 255, 0.05)",
        position: "relative",
      }}
    >
      {/* Header */}
      <div
        style={{
          width: "100%",
          padding: "12px 16px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          background: "linear-gradient(to bottom, rgba(0,0,0,0.8), transparent)",
          zIndex: 10,
        }}
      >
        <span style={{ fontSize: "12px", fontWeight: "600", color: "#fff", display: "flex", alignItems: "center", gap: "6px" }}>
          <Paintbrush size={14} style={{ color: "var(--accent-cyan)" }} />
          CANVAS IMAGE EDITOR
        </span>
        <button
          onClick={onClose}
          style={{
            background: "none",
            border: "none",
            color: "rgba(255,255,255,0.6)",
            cursor: "pointer",
          }}
        >
          <X size={16} />
        </button>
      </div>

      {/* Editor Screen */}
      <div
        style={{
          flex: 1,
          width: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "20px",
          overflow: "hidden",
        }}
      >
        {!imageSrc ? (
          /* Dropzone Placeholder */
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleFileDrop}
            style={{
              width: "100%",
              height: "100%",
              border: "1.5px dashed rgba(255,255,255,0.08)",
              borderRadius: "12px",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: "10px",
              cursor: "pointer",
            }}
            onClick={() => document.getElementById("editor-file-picker")?.click()}
          >
            <input
              id="editor-file-picker"
              type="file"
              accept="image/*"
              style={{ display: "none" }}
              onChange={handleFileChange}
            />
            <Paintbrush size={24} style={{ color: "var(--text-muted)" }} />
            <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
              Drag image here or click to load
            </span>
          </div>
        ) : (
          /* Image Canvas Container */
          <div style={{ position: "relative", boxShadow: "0 8px 32px rgba(0,0,0,0.5)" }}>
            <canvas
              ref={canvasRef}
              onMouseDown={startDrawing}
              onMouseMove={draw}
              onMouseUp={stopDrawing}
              onMouseLeave={stopDrawing}
              onTouchStart={startDrawingTouch}
              onTouchMove={drawTouch}
              onTouchEnd={stopDrawing}
              style={{
                display: "block",
                cursor: "crosshair",
                borderRadius: "4px",
                maxWidth: "100%",
                maxHeight: "260px",
                touchAction: "none",
              }}
            />
          </div>
        )}
      </div>

      {/* Brush Settings & Controls */}
      {imageSrc && (
        <div
          style={{
            width: "100%",
            padding: "8px 16px",
            background: "rgba(10, 10, 18, 0.95)",
            borderTop: "1px solid rgba(255, 255, 255, 0.05)",
            display: "flex",
            flexDirection: "column",
            gap: "10px",
          }}
        >
          {/* Colors and brush width */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ display: "flex", gap: "6px" }}>
              {neonColors.map((col) => (
                <button
                  key={col}
                  onClick={() => setBrushColor(col)}
                  style={{
                    width: "18px",
                    height: "18px",
                    borderRadius: "50%",
                    backgroundColor: col,
                    border: brushColor === col ? "2px solid #fff" : "1px solid rgba(255,255,255,0.2)",
                    cursor: "pointer",
                    padding: 0,
                  }}
                />
              ))}
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>Width:</span>
              <input
                type="range"
                min="1"
                max="20"
                value={brushWidth}
                onChange={(e) => setBrushWidth(parseInt(e.target.value))}
                style={{
                  width: "80px",
                  accentColor: "var(--accent-cyan)",
                }}
              />
              <span style={{ fontSize: "10px", color: "var(--text-secondary)", width: "20px" }}>{brushWidth}px</span>
            </div>
          </div>
        </div>
      )}

      {/* Editor Action Footer */}
      <div
        style={{
          width: "100%",
          padding: "12px 16px",
          background: "rgba(10, 10, 18, 0.95)",
          borderTop: "1px solid rgba(255, 255, 255, 0.05)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "12px",
        }}
      >
        {imageSrc ? (
          <>
            <div style={{ display: "flex", gap: "8px" }}>
              <button
                onClick={handleUndo}
                disabled={history.length <= 1}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "4px",
                  background: "none",
                  border: "1px solid rgba(255, 255, 255, 0.05)",
                  color: history.length <= 1 ? "var(--text-muted)" : "var(--text-secondary)",
                  padding: "6px 12px",
                  borderRadius: "6px",
                  cursor: history.length <= 1 ? "not-allowed" : "pointer",
                  fontSize: "11px",
                }}
              >
                <Undo size={11} />
                Undo
              </button>
              <button
                onClick={handleClear}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "4px",
                  background: "none",
                  border: "1px solid rgba(255, 255, 255, 0.05)",
                  color: "var(--text-secondary)",
                  padding: "6px 12px",
                  borderRadius: "6px",
                  cursor: "pointer",
                  fontSize: "11px",
                }}
              >
                <Trash2 size={11} />
                Reset
              </button>
            </div>

            <div style={{ display: "flex", gap: "8px" }}>
              <button
                onClick={() => setImageSrc(null)}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  background: "rgba(255, 255, 255, 0.02)",
                  border: "1px solid rgba(255, 255, 255, 0.05)",
                  color: "var(--text-secondary)",
                  padding: "6px 12px",
                  borderRadius: "6px",
                  cursor: "pointer",
                  fontSize: "11px",
                }}
              >
                Change Image
              </button>
              <button
                onClick={handleConfirm}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "4px",
                  background: "var(--accent-cyan)",
                  border: "none",
                  color: "#000",
                  padding: "6px 14px",
                  borderRadius: "6px",
                  cursor: "pointer",
                  fontSize: "11px",
                  fontWeight: "600",
                  boxShadow: "var(--glow-cyan)",
                }}
              >
                <Check size={11} />
                Use Image
              </button>
            </div>
          </>
        ) : (
          <span style={{ fontSize: "11px", color: "var(--text-muted)", width: "100%", textAlign: "center" }}>
            Select or drag an image to begin drawing.
          </span>
        )}
      </div>
    </div>
  );
}
