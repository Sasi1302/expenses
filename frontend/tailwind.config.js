/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'bg-primary': '#0f111a',
        'bg-secondary': '#1a1d2d',
        'bg-card': 'rgba(26, 29, 45, 0.7)',
        'text-primary': '#ffffff',
        'text-secondary': '#94a3b8',
        'accent-primary': '#6366f1',
        'accent-secondary': '#8b5cf6',
        'success': '#10b981',
        'danger': '#ef4444',
        'warning': '#f59e0b',
        'border': 'rgba(255, 255, 255, 0.1)',
        'glass-border': 'rgba(255, 255, 255, 0.05)',
      },
      fontFamily: {
        sans: ['Outfit', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
