# Prose Styles Documentation

## Overview

This document describes the standardized prose styling system implemented to ensure consistent markdown rendering across all components in the Open Notebook application.

## Problem Solved

Previously, different components used inconsistent prose class configurations:

- **StreamingResponse**: `prose prose-sm max-w-none dark:prose-invert`
- **ChatPanel**: `prose prose-sm prose-neutral dark:prose-invert max-w-none`
- **SourceDetailContent**: `prose prose-sm prose-neutral dark:prose-invert max-w-none`

This led to visual inconsistencies across different parts of the application.

## Solution

### New Utility: `prose-styles.ts`

A comprehensive utility that provides:
- **Standardized base classes** for all markdown rendering
- **Context-specific styles** for different use cases
- **Enhanced typography** with better spacing and visual hierarchy
- **Consistent color schemes** and link styling
- **Improved code styling** and syntax highlighting preparation

### Usage

#### Basic Usage
```typescript
import { getProseStyle } from '@/lib/utils/prose-styles'

// For chat messages
<div className={getProseStyle('chat')}>
  <ReactMarkdown>{content}</ReactMarkdown>
</div>

// For streaming responses
<div className={getProseStyle('streaming')}>
  <ReactMarkdown>{content}</ReactMarkdown>
</div>
```

#### Advanced Usage
```typescript
import { getProseClasses, PROSE_STYLES } from '@/lib/utils/prose-styles'

// Using predefined styles
<div className={PROSE_STYLES.DEFAULT()}>
  <ReactMarkdown>{content}</ReactMarkdown>
</div>

// Custom configuration
<div className={getProseClasses({
  size: 'lg',
  maxWidth: true,
  variant: 'neutral',
  customClasses: 'mt-4 mb-8'
})}>
  <ReactMarkdown>{content}</ReactMarkdown>
</div>
```

## Available Styles

### 1. `getProseStyle(context)` - Context-Based Styles

| Context | Use Case | Description |
|---------|----------|-------------|
| `'chat'` | Chat messages, AI responses | Standard styling for chat interfaces |
| `'streaming'` | Streaming responses | Tighter spacing for real-time content |
| `'source'` | Source content, insights | Optimized for document content |
| `'document'` | Full documents | Larger text size for reading |
| `'compact'` | UI elements, tooltips | Minimal styling for tight spaces |

### 2. `PROSE_STYLES` - Predefined Styles

```typescript
PROSE_STYLES.DEFAULT()    // Standard chat styling
PROSE_STYLES.STREAMING()  // Streaming response styling
PROSE_STYLES.SOURCE()     // Source content styling
PROSE_STYLES.DOCUMENT()   // Document styling (larger text)
PROSE_STYLES.COMPACT()    // Compact styling
```

### 3. `getProseClasses(options)` - Custom Configuration

Options:
- `size?: 'xs' | 'sm' | 'base' | 'lg' | 'xl'` - Text size
- `maxWidth?: boolean` - Whether to apply max-width constraint
- `variant?: 'neutral' | 'default'` - Color variant
- `customClasses?: string` - Additional custom classes

## Enhanced Features

### Improved Typography
- **Better heading hierarchy** with consistent sizing and spacing
- **Enhanced paragraph spacing** for readability
- **Improved list styling** with custom markers
- **Better link styling** with hover states

### Code Styling
- **Enhanced inline code** with background and padding
- **Pre-block styling** with borders and scrolling
- **Monospace font** for code elements
- **Syntax highlighting ready** structure

### Block Elements
- **Blockquotes** with left border and italic styling
- **Tables** with proper borders and spacing
- **Horizontal rules** with consistent spacing
- **Strong/emphasis** with proper font weights

## Migration Guide

### Before (Inconsistent)
```typescript
// StreamingResponse.tsx
<div className="prose prose-sm max-w-none dark:prose-invert break-words prose-a:break-all prose-p:leading-relaxed prose-headings:mt-4 prose-headings:mb-2">

// ChatPanel.tsx
<div className="prose prose-sm prose-neutral dark:prose-invert max-w-none break-words prose-headings:font-semibold prose-a:text-blue-600 prose-a:break-all prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-p:mb-4 prose-p:leading-7 prose-li:mb-2">

// SourceDetailContent.tsx
<div className="prose prose-sm prose-neutral dark:prose-invert max-w-none prose-headings:font-semibold prose-a:text-blue-600 prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-p:mb-4 prose-p:leading-7 prose-li:mb-2">
```

### After (Consistent)
```typescript
// All components now use:
import { getProseStyle } from '@/lib/utils/prose-styles'

// StreamingResponse.tsx
<div className={getProseStyle('streaming')}>

// ChatPanel.tsx
<div className={getProseStyle('chat')}>

// SourceDetailContent.tsx
<div className={getProseStyle('source')}>
```

## Benefits

1. **Consistency**: All markdown content now looks identical across components
2. **Maintainability**: Single source of truth for styling rules
3. **Flexibility**: Easy to customize for different contexts
4. **Enhanced UX**: Better typography and spacing for readability
5. **Future-Proof**: Easy to add new styles or modify existing ones

## Components Updated

- ✅ `StreamingResponse.tsx` - Uses `'streaming'` style
- ✅ `ChatPanel.tsx` - Uses `'chat'` style
- ✅ `SourceDetailContent.tsx` - Uses `'source'` style
- ✅ `SourceInsightDialog.tsx` - Uses `'source'` style
- ✅ `TransformationPlayground.tsx` - Uses `'default'` style

## Testing

Test file: `frontend/src/lib/utils/__tests__/prose-styles.test.ts`

Run tests to verify styling works correctly:
```bash
npm test prose-styles.test.ts
```

## Future Enhancements

- **Syntax highlighting** integration with prism.js or highlight.js
- **Theme-aware styling** for better dark/light mode support
- **Responsive typography** that adapts to screen size
- **Accessibility improvements** with better contrast ratios
- **Performance optimizations** with CSS-in-JS or utility classes