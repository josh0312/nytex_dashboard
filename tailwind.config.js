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
    // Design System - Stat Card Components
    // Red Theme
    'stat-card-red',
    'stat-icon-red',
    'icon-red',
    'stat-value-red',
    // Blue Theme
    'stat-card-blue',
    'stat-icon-blue',
    'icon-blue',
    'stat-value-blue',
    // Indigo Theme
    'stat-card-indigo',
    'stat-icon-indigo',
    'icon-indigo',
    'stat-value-indigo',
    // Green Theme
    'stat-card-green',
    'stat-icon-green',
    'icon-green',
    'stat-value-green',
    // Yellow Theme
    'stat-card-yellow',
    'stat-icon-yellow',
    'icon-yellow',
    'stat-value-yellow',
    // Orange Theme
    'stat-card-orange',
    'stat-icon-orange',
    'icon-orange',
    'stat-value-orange',
    // Purple Theme
    'stat-card-purple',
    'stat-icon-purple',
    'icon-purple',
    'stat-value-purple',
    // Gray Theme
    'stat-card-gray',
    'stat-icon-gray',
    'icon-gray',
    'stat-value-gray',
    // Grid and Layout
    'stat-grid',
    'stat-content',
    'stat-text',
    'stat-label',
    'stat-icon-lg',
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
