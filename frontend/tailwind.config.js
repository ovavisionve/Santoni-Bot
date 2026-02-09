/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        santoni: {
          50: "#fff8ed",
          100: "#ffefd4",
          200: "#ffdba8",
          300: "#ffc170",
          400: "#ff9d37",
          500: "#ff8010",
          600: "#f06406",
          700: "#c74a07",
          800: "#9e3a0e",
          900: "#7f320f",
          950: "#451705",
        },
      },
    },
  },
  plugins: [],
};
