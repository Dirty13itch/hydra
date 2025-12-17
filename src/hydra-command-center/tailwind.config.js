/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    "./**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        surface: {
          base: '#0a0a0a',
          dim: '#0d0d0d',
          default: '#111111',
          raised: '#171717',
          highlight: '#222222',
        },
      },
      boxShadow: {
        'glow-emerald': '0 0 12px rgba(16, 185, 129, 0.4)',
        'glow-cyan': '0 0 12px rgba(6, 182, 212, 0.4)',
        'glow-red': '0 0 12px rgba(239, 68, 68, 0.4)',
      },
      keyframes: {
        slideIn: {
          '0%': { transform: 'translateX(20px)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        }
      },
      animation: {
        'pulse-fast': 'pulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'slide-in': 'slideIn 0.3s ease-out forwards',
        'scale-in': 'scaleIn 0.2s ease-out forwards',
      }
    }
  },
  plugins: [],
}
