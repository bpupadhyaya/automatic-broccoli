/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#ecfeff",
          500: "#06b6d4",
          700: "#0e7490"
        }
      }
    }
  },
  plugins: []
};
