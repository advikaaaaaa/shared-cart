/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#fff4ef",
          100: "#ffe4d6",
          500: "#e25b2c",
          600: "#c94a1f",
          700: "#a63b18",
        },
        ink: {
          900: "#1c1917",
          700: "#44403c",
          500: "#78716c",
        },
      },
      fontFamily: {
        sans: ["Source Sans 3", "Segoe UI", "sans-serif"],
        display: ["Fraunces", "Georgia", "serif"],
      },
    },
  },
  plugins: [],
};
