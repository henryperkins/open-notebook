/**
 * Standardized prose styling utilities for consistent markdown rendering across the application.
 *
 * This ensures all markdown content has consistent visual appearance regardless of where it's rendered.
 */

export interface ProseStyleOptions {
  size?: 'xs' | 'sm' | 'base' | 'lg' | 'xl'
  maxWidth?: boolean
  variant?: 'neutral' | 'default'
  customClasses?: string
}

/**
 * Get standardized prose classes for consistent markdown styling
 *
 * @param options - Configuration options for prose styling
 * @returns Complete className string for consistent markdown rendering
 */
export function getProseClasses(options: ProseStyleOptions = {}): string {
  const {
    size = 'sm',
    maxWidth = false,
    variant = 'neutral',
    customClasses = ''
  } = options

  const baseClasses = [
    'prose',
    `prose-${size}`,
  ]

  // Add variant (neutral for better contrast)
  if (variant === 'neutral') {
    baseClasses.push('prose-neutral')
  }

  // Dark mode support
  baseClasses.push('dark:prose-invert')

  // Max width control
  if (!maxWidth) {
    baseClasses.push('max-w-none')
  }

  // Standard text wrapping and breaking
  baseClasses.push('break-words', 'prose-a:break-all')

  // Enhanced link styling
  baseClasses.push(
    'prose-a:text-blue-600',
    'prose-a:no-underline',
    'hover:prose-a:underline',
    'prose-a:font-medium'
  )

  // Enhanced heading styling
  baseClasses.push(
    'prose-headings:font-semibold',
    'prose-headings:scroll-mt-20', // Better anchor link behavior
    'prose-h1:text-2xl',
    'prose-h2:text-xl',
    'prose-h3:text-lg',
    'prose-h1:mt-8',
    'prose-h1:mb-4',
    'prose-h2:mt-6',
    'prose-h2:mb-3',
    'prose-h3:mt-4',
    'prose-h3:mb-3',
    'prose-h4:mt-4',
    'prose-h4:mb-2',
    'prose-h5:mt-3',
    'prose-h5:mb-2',
    'prose-h6:mt-3',
    'prose-h6:mb-2'
  )

  // Enhanced paragraph styling
  baseClasses.push(
    'prose-p:mb-4',
    'prose-p:leading-7'
  )

  // Enhanced list styling
  baseClasses.push(
    'prose-ul:mb-4',
    'prose-ul:space-y-1',
    'prose-ol:mb-4',
    'prose-ol:space-y-1',
    'prose-li:mb-1',
    'prose-li:marker:text-blue-600'
  )

  // Enhanced code styling
  baseClasses.push(
    'prose-code:bg-muted',
    'prose-code:px-1.5',
    'prose-code:py-0.5',
    'prose-code:rounded',
    'prose-code:text-sm',
    'prose-code:font-mono',
    'prose-code:text-blue-600'
  )

  // Pre block styling
  baseClasses.push(
    'prose-pre:bg-muted',
    'prose-pre:border',
    'prose-pre:rounded-lg',
    'prose-pre:p-4',
    'prose-pre:overflow-x-auto',
    'prose-pre:text-sm'
  )

  // Blockquote styling
  baseClasses.push(
    'prose-blockquote:border-l-4',
    'prose-blockquote:border-blue-500',
    'prose-blockquote:pl-4',
    'prose-blockquote:italic',
    'prose-blockquote:not-italic:font-normal'
  )

  // Table styling
  baseClasses.push(
    'prose-table:border-collapse',
    'prose-table:border',
    'prose-table:border-gray-200',
    'prose-th:border',
    'prose-th:border-gray-200',
    'prose-th:bg-muted',
    'prose-th:px-3',
    'prose-th:py-2',
    'prose-th:text-left',
    'prose-td:border',
    'prose-td:border-gray-200',
    'prose-td:px-3',
    'prose-td:py-2'
  )

  // Horizontal rule styling
  baseClasses.push(
    'prose-hr:border-gray-200',
    'prose-hr:my-6'
  )

  // Strong/bold styling
  baseClasses.push(
    'prose-strong:font-semibold',
    'prose-strong:text-foreground'
  )

  // Emphasis/italic styling
  baseClasses.push(
    'prose-em:italic'
  )

  // Custom classes
  if (customClasses) {
    baseClasses.push(customClasses)
  }

  return baseClasses.join(' ')
}

/**
 * Pre-defined prose style configurations for common use cases
 */
export const PROSE_STYLES = {
  /** Default style for chat messages and responses */
  DEFAULT: () => getProseClasses({
    size: 'sm',
    maxWidth: false,
    variant: 'neutral'
  }),

  /** Style for streaming responses with tighter spacing */
  STREAMING: () => getProseClasses({
    size: 'sm',
    maxWidth: false,
    variant: 'neutral',
    customClasses: 'prose-p:leading-relaxed prose-headings:mt-4 prose-headings:mb-2'
  }),

  /** Style for source content and insights */
  SOURCE: () => getProseClasses({
    size: 'sm',
    maxWidth: false,
    variant: 'neutral'
  }),

  /** Style for document content with larger text */
  DOCUMENT: () => getProseClasses({
    size: 'base',
    maxWidth: false,
    variant: 'neutral'
  }),

  /** Compact style for UI elements */
  COMPACT: () => getProseClasses({
    size: 'xs',
    maxWidth: false,
    variant: 'neutral',
    customClasses: 'prose-p:mb-2 prose-headings:mb-2'
  })
} as const

/**
 * Helper function to get the appropriate prose style for a given context
 */
export function getProseStyle(context: 'chat' | 'streaming' | 'source' | 'document' | 'compact'): string {
  switch (context) {
    case 'chat':
      return PROSE_STYLES.DEFAULT()
    case 'streaming':
      return PROSE_STYLES.STREAMING()
    case 'source':
      return PROSE_STYLES.SOURCE()
    case 'document':
      return PROSE_STYLES.DOCUMENT()
    case 'compact':
      return PROSE_STYLES.COMPACT()
    default:
      return PROSE_STYLES.DEFAULT()
  }
}