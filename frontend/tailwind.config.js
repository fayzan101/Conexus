/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0b1220",
          900: "#121a2b",
          800: "#1b2740",
          700: "#2a3a58",
        },
        accent: {
          DEFAULT: "#2f6fed",
          soft: "#e8f0ff",
        },
        sand: {
          50: "#f7f5f1",
          100: "#efeae2",
        },
      },
      fontFamily: {
        display: ['"Source Serif 4"', "Georgia", "serif"],
        sans: ['"IBM Plex Sans"', "Segoe UI", "sans-serif"],
      },
    },
  },
  plugins: [],
};
