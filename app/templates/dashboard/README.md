# Dashboard Implementation

## Dark Mode Implementation

The dashboard uses Tailwind CSS with Alpine.js for dark mode functionality. Here's how it works:

1. **Root Configuration (base.html)**
   ```html
   <html lang="en" class="h-full" 
         x-data="{ darkMode: localStorage.getItem('darkMode') === 'true' }" 
         x-init="..."
         :class="{ 'dark': darkMode }">
   ```
   - Dark mode state is managed at the root level using Alpine.js
   - The state is persisted in localStorage
   - The `dark` class is applied to the HTML root element

2. **Component Dark Mode Classes**
   - Components use Tailwind's dark mode classes with the following pattern:
   ```html
   <div class="bg-{color}-100 dark:bg-{color}-800">
   ```
   - Light mode uses lower intensity colors (e.g., 100, 200)
   - Dark mode uses higher intensity colors (e.g., 700, 800)
   - Avoid using opacity modifiers (e.g., `/40`) as they can cause inconsistencies

3. **Working Examples**
   - Total Sales Card:
     ```html
     <div class="bg-indigo-100 dark:bg-indigo-800">
         <div class="bg-indigo-200 dark:bg-indigo-700">  <!-- Icon background -->
             <svg class="text-indigo-600 dark:text-indigo-400">  <!-- Icon color -->
     ```
   - Total Orders Card:
     ```html
     <div class="bg-blue-100 dark:bg-blue-800">
         <div class="bg-blue-200 dark:bg-blue-700">  <!-- Icon background -->
             <svg class="text-blue-600 dark:text-blue-400">  <!-- Icon color -->
     ```

## Component Structure

1. **Top Row Metrics**
   - Total Sales (indigo theme)
   - Total Orders (blue theme)
   - Seasonal Sales (green theme)
   - Low Item Stock Items (red theme)

2. **Bottom Section**
   - Location Sales Table (left column)
   - Future Component Placeholder (right column)

## Best Practices

1. **Color Consistency**
   - Light mode backgrounds: `{color}-50` or `{color}-100`
   - Light mode accents: `{color}-200`
   - Light mode text: `{color}-600`
   - Dark mode backgrounds: `{color}-800`
   - Dark mode accents: `{color}-700`
   - Dark mode text: `{color}-300` or `{color}-400`

2. **Component Layout**
   - Use consistent padding (`p-4`)
   - Maintain consistent spacing (`gap-4`)
   - Use responsive grid layouts (`grid-cols-1 md:grid-cols-2 lg:grid-cols-4`)

3. **Loading States**
   - Include skeleton loaders for dynamic content
   - Use `animate-pulse` for loading animations
   - Match dark mode colors in loading states 