# 📚 Help Documentation System

This directory contains user-facing help documentation that is automatically discovered and displayed in the help center.

## 🚀 How It Works

The help system automatically scans this directory for `.md` files and displays them in the help center. No code changes required!

## 📝 Adding New Help Documentation

### 1. Create a New Markdown File

Create a new `.md` file in this directory with a descriptive filename:

```bash
# Examples:
items.md           # For Items/Inventory help
admin.md          # For Admin section help
troubleshooting.md # For troubleshooting guide
```

### 2. Add Frontmatter

Start your file with YAML frontmatter to control how it appears:

```yaml
---
title: "Your Page Title"
description: "Brief description for the help center"
icon: "lucide-icon-name"
order: 5
---
```

**Frontmatter Options:**
- `title`: Display name in help center (required)
- `description`: Short description shown on help index
- `icon`: Lucide icon name (without "lucide-" prefix)
- `order`: Sort order (lower numbers appear first)

### 3. Write Your Content

Use Markdown with rich formatting like the existing files:

```markdown
# 🎯 Your Help Topic

> **Brief description or quote to grab attention**

## 📊 Section with Table

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Data     | More data| Even more|

## 🚀 Step-by-Step Process

### **Step 1: Do Something**
```bash
1. First action
2. Second action
3. Third action
```

## 💡 Pro Tips

> **Tip**: Use blockquotes for important tips and advice

## 🛠️ Troubleshooting

### ❌ **Common Problem**
```bash
✅ Solution:
1. Try this first
2. Then try this
3. Contact support if needed
```
```

### 4. Test Your Changes

1. Save your file
2. Restart the application (if needed)
3. Visit `/help/` to see your new documentation
4. Click on your new help topic to test it

## 🎨 Formatting Guidelines

### Icons and Emojis
Use emojis and icons liberally to make content visually appealing:
- 🎯 for goals/objectives
- 📊 for data/analytics
- 🚀 for getting started/processes
- 💡 for tips
- 🛠️ for troubleshooting
- ✅ for solutions
- ❌ for problems

### Code Blocks
Use code blocks for step-by-step instructions:
```bash
1. Step one
2. Step two
3. Step three
```

### Tables
Use tables for structured information:
| Feature | Description | Benefit |
|---------|-------------|---------|
| Thing   | What it does| Why it's good |

### Blockquotes
Use blockquotes for important information:
> **Important**: This is something users should pay attention to

## 📁 File Naming

- Use lowercase with hyphens: `getting-started.md`
- Be descriptive: `inventory-management.md` not `inv.md`
- Match the URL you want: `reports.md` → `/help/reports`

## 🔄 Automatic Features

The system automatically:
- ✅ Discovers new `.md` files
- ✅ Sorts by `order` then `title`
- ✅ Generates navigation
- ✅ Creates cross-reference links
- ✅ Processes markdown to HTML
- ✅ Applies consistent styling

## 🎯 Best Practices

1. **Start with frontmatter** - Always include title and description
2. **Use rich formatting** - Tables, code blocks, emojis, icons
3. **Be user-focused** - Write for people using the website, not developers
4. **Include examples** - Show real examples and use cases
5. **Add troubleshooting** - Include common problems and solutions
6. **Test thoroughly** - Make sure your content displays correctly

## 📚 Examples

Look at existing files for inspiration:
- `getting-started.md` - Overview and navigation
- `dashboard.md` - Feature-specific help
- `reports.md` - Process-focused help
- `catalog.md` - Integration-focused help

---

🎉 **Happy documenting!** Your users will appreciate clear, helpful documentation. 