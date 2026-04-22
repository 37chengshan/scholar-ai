import React from "react";

export function Logo() {
  return (
    <div className="flex items-center gap-3">
      <div className="relative shrink-0" style={{ width: 40, height: 40 }}>
        <svg
          viewBox="0 0 90 90"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="w-full h-full"
        >
          <circle cx="34" cy="45" r="24" stroke="currentColor" strokeWidth="3" fill="none" className="text-foreground" />
          <circle cx="56" cy="45" r="24" stroke="currentColor" strokeWidth="3" fill="none" className="text-primary" />
          <path d="M45 25C45 25 41 35 41 45C41 55 45 65 45 65" stroke="currentColor" strokeWidth="2" fill="none" opacity="0.5" className="text-primary" />
          <text x="30" y="50" textAnchor="middle" fontFamily="Libre Bodoni, serif" fontSize="16" fontWeight="600" className="fill-foreground">S</text>
          <text x="60" y="50" textAnchor="middle" fontFamily="Public Sans, sans-serif" fontSize="13" fontWeight="700" className="fill-primary">AI</text>
          <circle cx="45" cy="27" r="2" className="fill-primary" />
          <circle cx="45" cy="63" r="2" className="fill-primary" />
          <path d="M30 74C30 74 38 78 45 78C52 78 60 74 60 74" stroke="currentColor" strokeWidth="1" fill="none" strokeLinecap="round" opacity="0.4" className="text-primary" />
        </svg>
      </div>
      <span
        className="text-2xl font-semibold tracking-wide text-foreground"
        style={{ fontFamily: "'Libre Bodoni', serif", fontStyle: "italic" }}
      >
        ScholarAI
      </span>
    </div>
  );
}