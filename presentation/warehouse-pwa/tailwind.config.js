/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#EBF2FC', 100: '#D6E6F9', 200: '#ADCCF3',
          300: '#84B3ED', 400: '#5B99E7', 500: '#4A90E2',
          600: '#3A73B5', 700: '#2B5688', 800: '#1F4E78',
          900: '#0F2740',
        },
      },
    },
  },
  plugins: [],
};
