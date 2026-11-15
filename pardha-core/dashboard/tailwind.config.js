/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["Space Grotesk", "Inter", "ui-sans-serif", "sans-serif"],
      },
      colors: {
        ink: "#101314",
        canvas: "#f4f3ee",
        acid: "#c7f36b",
        coral: "#ff6f59",
      },
      boxShadow: {
        card: "0 18px 50px rgba(16, 19, 20, 0.08)",
      },
    },
  },
  plugins: [],
};
