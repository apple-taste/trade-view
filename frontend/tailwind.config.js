/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'jojo-gold': '#FFD700',
        'jojo-gold-dark': '#FFA500',
        'jojo-blue': '#1a1a2e',
        'jojo-blue-light': '#16213e',
        'jojo-red': '#c41e3a',
        'jojo-red-dark': '#8b0000',
        'jojo-purple': '#6a0dad',
        'jojo-pink': '#ff69b4',
      },
      fontFamily: {
        'jojo': ['Arial Black', 'Arial', 'sans-serif'],
      },
      animation: {
        'jojo-pulse': 'jojo-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'jojo-glow': 'jojo-glow 2s ease-in-out infinite alternate',
        'jojo-shake': 'jojo-shake 0.5s ease-in-out',
      },
      keyframes: {
        'jojo-pulse': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
        'jojo-glow': {
          '0%': { boxShadow: '0 0 5px #FFD700, 0 0 10px #FFD700' },
          '100%': { boxShadow: '0 0 10px #FFD700, 0 0 20px #FFD700, 0 0 30px #FFD700' },
        },
        'jojo-shake': {
          '0%, 100%': { transform: 'translateX(0)' },
          '25%': { transform: 'translateX(-5px)' },
          '75%': { transform: 'translateX(5px)' },
        },
      },
    },
  },
  plugins: [],
}
