"use client";

import Link from "next/link";
import { useRef, useState, type MouseEvent, type ReactNode } from "react";

interface MagneticButtonProps {
  href: string;
  children: ReactNode;
  variant?: "primary" | "secondary";
  className?: string;
}

export default function MagneticButton({
  href,
  children,
  variant = "primary",
  className = "",
}: MagneticButtonProps) {
  const ref = useRef<HTMLAnchorElement>(null);
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  const handleMove = (e: MouseEvent<HTMLAnchorElement>) => {
    const el = ref.current;
    if (!el) return;

    const rect = el.getBoundingClientRect();
    setOffset({
      x: (e.clientX - rect.left - rect.width / 2) * 0.2,
      y: (e.clientY - rect.top - rect.height / 2) * 0.2,
    });
  };

  const handleLeave = () => setOffset({ x: 0, y: 0 });

  return (
    <Link
      ref={ref}
      href={href}
      className={`landing-btn landing-btn--${variant} ${className}`}
      style={{ transform: `translate(${offset.x}px, ${offset.y}px)` }}
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
      data-cursor-hover
    >
      {children}
    </Link>
  );
}
