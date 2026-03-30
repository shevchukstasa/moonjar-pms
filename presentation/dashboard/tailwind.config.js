/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#EBF2FC', 100: '#D6E6F9', 200: '#ADCCF3',
          300: '#84B3ED', 400: '#5B99E7', 500: '#4A90E2',
          600: '#3A73B5', 700: '#2B5688', 800: '#1F4E78',
          900: '#0F2740',
        },
        stone: {
          50: '#fafaf9', 100: '#f5f5f4', 200: '#e7e5e4',
          300: '#d6d3d1', 400: '#a8a29e', 500: '#78716c',
          600: '#57534e', 700: '#44403c', 800: '#292524',
          900: '#1c1917', 950: '#0c0a09',
        },
        gold: {
          50: '#fdf8f0', 100: '#faecd8', 200: '#f4d5a8',
          300: '#edb86e', 400: '#e5993a', 500: '#d4a574',
          600: '#c47f2a', 700: '#a3621e', 800: '#854d1d', 900: '#6c3f1d',
        },
        surface: {
          DEFAULT: '#ffffff',
          dark: '#1a1814',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
