import React from 'react';
import { motion } from 'framer-motion';

interface ButtonProps {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'ghost' | 'neon';
  size?: 'sm' | 'md' | 'lg';
  onClick?: () => void;
  className?: string;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  onClick,
  className = '',
}) => {
  const baseStyles = 'relative font-display font-semibold uppercase tracking-wider rounded-lg overflow-hidden transition-all duration-300';

  const sizeStyles = {
    sm: 'px-4 py-2 text-xs',
    md: 'px-6 py-3 text-sm',
    lg: 'px-8 py-4 text-sm',
  };

  const variantStyles = {
    primary: `
      bg-gradient-to-r from-cyan-500 to-blue-600 text-white
      hover:shadow-[0_0_30px_rgba(0,245,255,0.5)] hover:scale-105
      active:scale-95
    `,
    secondary: `
      bg-white/10 text-white border border-white/20
      hover:bg-white/20 hover:border-white/30
      active:scale-95
    `,
    ghost: `
      border border-cyan-500/50 text-cyan-400
      hover:border-cyan-400 hover:text-cyan-300
      hover:shadow-[0_0_20px_rgba(0,245,255,0.3)] hover:bg-cyan-500/10
      active:scale-95
    `,
    neon: `
      bg-cyan-500 text-black
      hover:shadow-[0_0_40px_rgba(0,245,255,0.6)] hover:scale-105
      active:scale-95
    `,
  };

  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      className={`${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
    >
      <span className="relative z-10 flex items-center justify-center gap-2">
        {children}
      </span>
    </motion.button>
  );
};
