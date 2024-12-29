/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    "./app/templates/**/*.html",
    "./app/static/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        // You can add custom colors here
      },
    },
  },
  plugins: [],
}
