/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        dark: {
          950: '#0d1117',
          900: '#161b22',
          800: '#21262d',
          700: '#30363d',
          600: '#484f58',
          500: '#6e7681',
          400: '#8b949e',
          300: '#b1bac4',
          200: '#c9d1d9',
          100: '#e6edf3',
        },
        brand: {
          blue: '#1f6feb',
          blueHover: '#388bfd',
          green: '#238636',
          greenHover: '#2ea043',
          red: '#da3633',
          purple: '#8957e5',
          yellow: '#d29922',
        },
      },
    },
  },
  plugins: [],
}
