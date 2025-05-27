/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    "./app/templates/**/*.html",
    "./app/static/**/*.js",
  ],
  safelist: [
    'text-yellow-800',
    'bg-yellow-100',
    'dark:bg-white',
    'dark:text-yellow-800',
    'bg-blue-600',
    'bg-blue-700',
    'hover:bg-blue-700',
    'dark:bg-blue-700',
    'dark:hover:bg-blue-600',
    'text-white',
    'dark:text-white',
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
