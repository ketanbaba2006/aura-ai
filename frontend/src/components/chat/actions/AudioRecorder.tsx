"use client";

import { useEffect, useRef, useState } from "react";
import { Mic, Square, X, Check, Play, Pause, Trash } from "lucide-react";

interface AudioRecorderProps {
  onRecord: (file: File) => void;
  onClose: () => void;
}

export function AudioRecorder({ onRecord, onClose }: AudioRecorderProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const [stream, setStream] = useState<MediaStream | null>(null);
  const [recordingState, setRecordingState] = useState<"idle" | "recording" | "review">("idle");
  const [duration, setDuration] = useState(0);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);
  const durationIntervalRef = useRef<any>(null);

  // Initialize recording
  const startRecording = async () => {
    setAudioUrl(null);
    audioChunksRef.current = [];
    
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setStream(mediaStream);
      setRecordingState("recording");
      setDuration(0);

      // Set up MediaRecorder
      const options = { mimeType: "audio/webm" };
      let recorder: MediaRecorder;
      try {
        recorder = new MediaRecorder(mediaStream, options);
      } catch (e) {
        recorder = new MediaRecorder(mediaStream);
      }
      
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: recorder.mimeType || "audio/webm" });
        const url = URL.createObjectURL(audioBlob);
        setAudioUrl(url);
        setRecordingState("review");
        cleanupTracks(mediaStream);
      };

      // Set up AudioContext Analyser for visualizer
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const source = audioContext.createMediaStreamSource(mediaStream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);

      audioContextRef.current = audioContext;
      analyserRef.current = analyser;

      // Start duration timer
      durationIntervalRef.current = setInterval(() => {
        setDuration((prev) => prev + 1);
      }, 1000);

      recorder.start();
      drawWaveform();
    } catch (err) {
      console.error("Audio recording error:", err);
      alert("Microphone access denied or failed to initialize.");
      setRecordingState("idle");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && recordingState === "recording") {
      mediaRecorderRef.current.stop();
    }
    if (durationIntervalRef.current) {
      clearInterval(durationIntervalRef.current);
    }
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
  };

  const cleanupTracks = (mediaStream: MediaStream) => {
    mediaStream.getTracks().forEach((track) => track.stop());
    setStream(null);
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
    }
  };

  useEffect(() => {
    return () => {
      if (durationIntervalRef.current) clearInterval(durationIntervalRef.current);
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, [stream]);

  // Audio Playback during review
  const togglePlayback = () => {
    const player = audioPlayerRef.current;
    if (!player) return;

    if (isPlaying) {
      player.pause();
    } else {
      player.play();
    }
    setIsPlaying(!isPlaying);
  };

  const handleAudioEnded = () => {
    setIsPlaying(false);
  };

  // Waveform visualization using HTML5 Canvas
  const drawWaveform = () => {
    const canvas = canvasRef.current;
    const analyser = analyserRef.current;
    if (!canvas || !analyser) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const render = () => {
      if (recordingState !== "recording") return;

      animationFrameRef.current = requestAnimationFrame(render);
      analyser.getByteFrequencyData(dataArray);

      // Responsive sizing
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * window.devicePixelRatio;
      canvas.height = rect.height * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

      ctx.clearRect(0, 0, rect.width, rect.height);

      const barWidth = (rect.width / bufferLength) * 1.5;
      let barHeight;
      let x = 0;

      for (let i = 0; i < bufferLength; i++) {
        barHeight = (dataArray[i] / 255) * rect.height * 0.85;

        // Centered dynamic visual bars
        const y = (rect.height - barHeight) / 2;

        // Linear gradient matching AURA colors
        const grad = ctx.createLinearGradient(0, y, 0, y + barHeight);
        grad.addColorStop(0, "#06d6d6");
        grad.addColorStop(1, "#8b5cf6");

        ctx.fillStyle = grad;
        ctx.fillRect(x, y, barWidth - 2, barHeight);

        x += barWidth;
      }
    };

    render();
  };

  const handleConfirm = () => {
    if (!audioUrl) return;
    fetch(audioUrl)
      .then((res) => res.blob())
      .then((blob) => {
        const file = new File([blob], `voice_recording_${Date.now()}.wav`, {
          type: blob.type || "audio/wav",
        });
        onRecord(file);
      })
      .catch((err) => console.error("Failed to compile audio:", err));
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60).toString().padStart(2, "0");
    const s = (secs % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        width: "100%",
        height: "280px",
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
          <Mic size={14} style={{ color: "var(--accent-cyan)" }} />
          VOICE RECORDER
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

      {/* Visual Waveform Screen */}
      <div style={{ flex: 1, width: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "40px 20px 20px" }}>
        {recordingState === "recording" ? (
          <>
            <canvas ref={canvasRef} style={{ width: "100%", height: "80px" }} />
            <span style={{ fontSize: "28px", fontWeight: "700", color: "#fff", marginTop: "12px", fontVariantNumeric: "tab-regular-nums" }}>
              {formatTime(duration)}
            </span>
          </>
        ) : recordingState === "review" ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "12px" }}>
            <span style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Record Completed</span>
            <button
              onClick={togglePlayback}
              style={{
                width: "48px",
                height: "48px",
                borderRadius: "50%",
                background: "rgba(255,255,255,0.05)",
                border: "1px solid rgba(255,255,255,0.1)",
                color: "var(--accent-cyan)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                cursor: "pointer",
                outline: "none",
              }}
            >
              {isPlaying ? <Pause size={18} fill="currentColor" /> : <Play size={18} fill="currentColor" style={{ marginLeft: "2px" }} />}
            </button>
            <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Preview Audio</span>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "8px" }}>
            <div style={{ width: "48px", height: "48px", borderRadius: "50%", border: "1px dashed rgba(255,255,255,0.15)", display: "flex", alignItems: "center", justifyItems: "center", justifyContent: "center", color: "var(--text-muted)" }}>
              <Mic size={20} />
            </div>
            <span style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>Click record to capture voice input</span>
          </div>
        )}
      </div>

      {/* Hidden Audio element for playback */}
      {audioUrl && (
        <audio
          ref={audioPlayerRef}
          src={audioUrl}
          onEnded={handleAudioEnded}
          style={{ display: "none" }}
        />
      )}

      {/* Controls Footer */}
      <div
        style={{
          width: "100%",
          padding: "16px",
          background: "rgba(10, 10, 18, 0.95)",
          borderTop: "1px solid rgba(255, 255, 255, 0.05)",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          gap: "16px",
        }}
      >
        {recordingState === "recording" ? (
          <button
            onClick={stopRecording}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              background: "var(--error)",
              border: "none",
              color: "#fff",
              padding: "10px 20px",
              borderRadius: "8px",
              cursor: "pointer",
              fontSize: "12px",
              fontWeight: "600",
              boxShadow: "0 0 16px rgba(239, 68, 68, 0.2)",
            }}
          >
            <Square size={12} fill="#fff" />
            Stop Recording
          </button>
        ) : recordingState === "review" ? (
          <div style={{ display: "flex", gap: "12px", width: "100%" }}>
            <button
              onClick={() => {
                setRecordingState("idle");
                setAudioUrl(null);
              }}
              style={{
                flex: 1,
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "6px",
                background: "rgba(255, 255, 255, 0.03)",
                border: "1px solid rgba(255, 255, 255, 0.08)",
                color: "var(--text-secondary)",
                padding: "8px 16px",
                borderRadius: "8px",
                cursor: "pointer",
                fontSize: "12px",
                fontWeight: "600",
              }}
            >
              <Trash size={12} />
              Discard
            </button>
            <button
              onClick={handleConfirm}
              style={{
                flex: 1,
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
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
              Confirm Ingest
            </button>
          </div>
        ) : (
          <button
            onClick={startRecording}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              background: "linear-gradient(135deg, #06d6d6, #8b5cf6)",
              border: "none",
              color: "#000",
              padding: "10px 24px",
              borderRadius: "8px",
              cursor: "pointer",
              fontSize: "12px",
              fontWeight: "600",
              boxShadow: "0 0 15px rgba(6, 214, 214, 0.3)",
            }}
          >
            <Mic size={14} />
            Start Voice Capture
          </button>
        )}
      </div>
    </div>
  );
}
