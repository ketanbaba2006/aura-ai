"use client";

import { useEffect, useRef, useState } from "react";
import { Camera, RefreshCw, X, Check, RotateCcw } from "lucide-react";

interface CameraCaptureProps {
  onCapture: (file: File) => void;
  onClose: () => void;
}

export function CameraCapture({ onCapture, onClose }: CameraCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [useCountdown, setUseCountdown] = useState(false);
  const [isFlashActive, setIsFlashActive] = useState(false);

  // Initialize camera
  const startCamera = async () => {
    setError(null);
    setCapturedImage(null);
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { width: 1280, height: 720, facingMode: "user" },
        audio: false,
      });
      setStream(mediaStream);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
    } catch (err: any) {
      console.error("Camera access error:", err);
      setError("Unable to access camera. Please check permissions.");
    }
  };

  useEffect(() => {
    startCamera();
    return () => {
      // Clean up track on unmount
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  const handleCapture = () => {
    if (useCountdown) {
      setCountdown(3);
    } else {
      takeSnapshot();
    }
  };

  // Countdown handler
  useEffect(() => {
    if (countdown === null) return;
    if (countdown === 0) {
      setCountdown(null);
      takeSnapshot();
      return;
    }
    const timer = setTimeout(() => {
      setCountdown((prev) => (prev ? prev - 1 : 0));
    }, 1000);
    return () => clearTimeout(timer);
  }, [countdown]);

  const takeSnapshot = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !stream) return;

    // Trigger flash animation
    setIsFlashActive(true);
    setTimeout(() => setIsFlashActive(false), 150);

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Match dimensions
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    // Mirror image for natural user preview
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);

    // Draw frame
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Reset transform
    ctx.setTransform(1, 0, 0, 1, 0, 0);

    const dataUrl = canvas.toDataURL("image/jpeg", 0.9);
    setCapturedImage(dataUrl);

    // Turn off camera stream during review
    stream.getTracks().forEach((track) => track.stop());
    setStream(null);
  };

  const handleRetake = () => {
    startCamera();
  };

  const handleApprove = () => {
    if (!capturedImage) return;

    // Convert dataURL to Blob and then File
    fetch(capturedImage)
      .then((res) => res.blob())
      .then((blob) => {
        const file = new File([blob], `camera_capture_${Date.now()}.jpg`, {
          type: "image/jpeg",
        });
        onCapture(file);
      })
      .catch((err) => {
        console.error("Failed to approve photo:", err);
      });
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        width: "100%",
        height: "360px",
        position: "relative",
        background: "#05050a",
        borderRadius: "14px",
        overflow: "hidden",
        border: "1px solid rgba(255, 255, 255, 0.05)",
      }}
    >
      {/* Header Overlay */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          padding: "12px 16px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          background: "linear-gradient(to bottom, rgba(0,0,0,0.8), transparent)",
          zIndex: 10,
        }}
      >
        <span style={{ fontSize: "12px", fontWeight: "600", color: "#fff", display: "flex", alignItems: "center", gap: "6px" }}>
          <Camera size={14} style={{ color: "var(--accent-cyan)" }} />
          CAMERA CAPTURE
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

      {/* Screen area */}
      <div style={{ flex: 1, width: "100%", position: "relative", display: "flex", alignItems: "center", justifyContent: "center" }}>
        {error ? (
          <div style={{ color: "var(--error)", fontSize: "13px", padding: "20px", textAlign: "center" }}>
            {error}
          </div>
        ) : capturedImage ? (
          /* Captured Preview */
          <img
            src={capturedImage}
            alt="Capture Preview"
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
            }}
          />
        ) : (
          /* Live Stream */
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              transform: "scaleX(-1)", // Mirror viewport
            }}
          />
        )}

        {/* Camera Flash overlay */}
        
          {isFlashActive && (
            <div
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: "#fff",
                zIndex: 20,
              }}
            />
          )}
        

        {/* Countdown overlay */}
        
          {countdown !== null && (
            <div
              style={{
                position: "absolute",
                fontSize: "72px",
                fontWeight: "900",
                color: "var(--accent-cyan)",
                textShadow: "0 0 30px rgba(6, 214, 214, 0.6)",
                zIndex: 15,
              }}
            >
              {countdown}
            </div>
          )}
        
      </div>

      {/* Hidden Canvas */}
      <canvas ref={canvasRef} style={{ display: "none" }} />

      {/* Footer controls */}
      <div
        style={{
          width: "100%",
          padding: "16px",
          background: "rgba(10, 10, 18, 0.95)",
          borderTop: "1px solid rgba(255, 255, 255, 0.05)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "12px",
        }}
      >
        {capturedImage ? (
          <>
            <button
              onClick={handleRetake}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.08)",
                color: "var(--text-secondary)",
                padding: "8px 16px",
                borderRadius: "8px",
                cursor: "pointer",
                fontSize: "12px",
                fontWeight: "600",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.08)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.03)")}
            >
              <RotateCcw size={12} />
              Retake
            </button>
            <button
              onClick={handleApprove}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                background: "var(--accent-cyan)",
                border: "none",
                color: "#000",
                padding: "8px 16px",
                borderRadius: "8px",
                cursor: "pointer",
                fontSize: "12px",
                fontWeight: "600",
                boxShadow: "var(--glow-cyan)",
              }}
            >
              <Check size={12} />
              Confirm Photo
            </button>
          </>
        ) : (
          <>
            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                fontSize: "11px",
                color: "var(--text-muted)",
                cursor: "pointer",
                userSelect: "none",
              }}
            >
              <input
                type="checkbox"
                checked={useCountdown}
                onChange={(e) => setUseCountdown(e.target.checked)}
                style={{
                  accentColor: "var(--accent-cyan)",
                  width: "12px",
                  height: "12px",
                }}
              />
              3s Countdown timer
            </label>

            <button
              onClick={handleCapture}
              disabled={!!error || countdown !== null}
              style={{
                width: "44px",
                height: "44px",
                borderRadius: "50%",
                background: "linear-gradient(135deg, #06d6d6, #8b5cf6)",
                border: "none",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#000",
                cursor: "pointer",
                boxShadow: "0 0 15px rgba(6, 214, 214, 0.4)",
              }}
            >
              <Camera size={20} />
            </button>
            <div style={{ width: "80px" }} /> {/* spacer to center shutter */}
          </>
        )}
      </div>
    </div>
  );
}
