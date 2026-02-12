/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        santoni: {
          50: "#eef2ff",
          100: "#dce5ff",
          200: "#c2d1ff",
          300: "#97b1ff",
          400: "#6a88ff",
          500: "#3d5cf7",
          600: "#042387",
          700: "#031c6e",
          800: "#021556",
          900: "#010f3e",
          950: "#0b1530",
        },
      },
    },
  },
  plugins: [],
};
