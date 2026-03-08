/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        tv: {
          bg: '#ffffff',
          panel: '#f0f3fa',
          border: '#e0e3eb',
          text: '#131722',
          muted: '#787b86',
          blue: '#2962ff',
          red: '#ef5350',
          green: '#26a069',
        }
      }
    },
  },
  plugins: [],
}
