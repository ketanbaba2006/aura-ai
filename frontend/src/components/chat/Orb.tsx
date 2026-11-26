"use client";

export type OrbStatus = "idle" | "thinking" | "searching" | "reasoning" | "streaming";

interface OrbProps {
  status?: OrbStatus;
  size?: "sm" | "md" | "lg";
}

const SIZES = { sm: 32, md: 64, lg: 140 } as const;

export function Orb({ status = "idle", size = "md" }: OrbProps) {
  const dim = SIZES[size];

  const getStatusColor = () => {
    switch (status) {
      case "thinking": return "#8b5cf6";
      case "searching": return "#3b82f6";
      case "reasoning": return "#ec4899";
      case "streaming": return "#06d6d6";
      default: return "#06d6d6";
    }
  };

  const color = getStatusColor();

  return (
    <div
      style={{
        width: dim,
        height: dim,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "transparent",
        position: "relative"
      }}
    >
      <img 
        src="/aura-logo.png" 
        alt="AURA AI Logo"
        className="animate-3d-logo"
        style={{
          width: "70%",
          height: "70%",
          objectFit: "contain",
          filter: `drop-shadow(0 0 5px ${color})`
        }} 
      />
    </div>
  );
}
