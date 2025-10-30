/**
 * Utility functions for formatting various data types in a user-friendly way.
 */

/**
 * Format file size in bytes to human readable string
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes'

  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

/**
 * Format duration in seconds to human readable string
 */
export function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${Math.round(seconds)}s`
  }

  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60

  if (minutes < 60) {
    return `${minutes}m ${Math.round(remainingSeconds)}s`
  }

  const hours = Math.floor(minutes / 60)
  const remainingMinutes = minutes % 60

  if (hours < 24) {
    return `${hours}h ${remainingMinutes}m`
  }

  const days = Math.floor(hours / 24)
  const remainingHours = hours % 24

  return `${days}d ${remainingHours}h`
}

/**
 * Format time remaining in seconds to human readable string
 */
export function formatTimeRemaining(seconds: number): string {
  if (seconds < 0) return '--'
  if (seconds < 10) return 'A few seconds'
  return formatDuration(seconds)
}

/**
 * Format percentage to human readable string with proper precision
 */
export function formatPercentage(value: number, precision = 1): string {
  return `${value.toFixed(precision)}%`
}

/**
 * Format date to relative time string (e.g., "2 hours ago")
 */
export function formatRelativeTime(date: Date | string): string {
  const now = new Date()
  const past = typeof date === 'string' ? new Date(date) : date
  const diffInSeconds = Math.floor((now.getTime() - past.getTime()) / 1000)

  if (diffInSeconds < 60) {
    return 'Just now'
  }

  const diffInMinutes = Math.floor(diffInSeconds / 60)
  if (diffInMinutes < 60) {
    return `${diffInMinutes} minute${diffInMinutes > 1 ? 's' : ''} ago`
  }

  const diffInHours = Math.floor(diffInMinutes / 60)
  if (diffInHours < 24) {
    return `${diffInHours} hour${diffInHours > 1 ? 's' : ''} ago`
  }

  const diffInDays = Math.floor(diffInHours / 24)
  if (diffInDays < 7) {
    return `${diffInDays} day${diffInDays > 1 ? 's' : ''} ago`
  }

  const diffInWeeks = Math.floor(diffInDays / 7)
  if (diffInWeeks < 4) {
    return `${diffInWeeks} week${diffInWeeks > 1 ? 's' : ''} ago`
  }

  const diffInMonths = Math.floor(diffInDays / 30)
  if (diffInMonths < 12) {
    return `${diffInMonths} month${diffInMonths > 1 ? 's' : ''} ago`
  }

  const diffInYears = Math.floor(diffInDays / 365)
  return `${diffInYears} year${diffInYears > 1 ? 's' : ''} ago`
}

/**
 * Format date to readable string
 */
export function formatDate(date: Date | string, options: Intl.DateTimeFormatOptions = {}): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date
  return dateObj.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    ...options,
  })
}

/**
 * Format date with time
 */
export function formatDateTime(date: Date | string): string {
  return formatDate(date, {
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * Format speed (bytes per second) to human readable string
 */
export function formatUploadSpeed(bytesPerSecond: number): string {
  if (bytesPerSecond === 0) return '0 B/s'
  return `${formatFileSize(bytesPerSecond)}/s`
}

/**
 * Format a large number with K, M, B suffixes
 */
export function formatNumber(num: number): string {
  if (num >= 1000000000) {
    return `${(num / 1000000000).toFixed(1)}B`
  }
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`
  }
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`
  }
  return num.toString()
}

/**
 * Format currency amount
 */
export function formatCurrency(amount: number, currency = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
  }).format(amount)
}

/**
 * Truncate text to specified length with ellipsis
 */
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return `${text.slice(0, maxLength)}...`
}

/**
 * Format API error messages to user-friendly text
 */
export function formatErrorMessage(error: any): string {
  if (typeof error === 'string') return error

  if (error?.response?.data?.detail) {
    return error.response.data.detail
  }

  if (error?.message) {
    return error.message
  }

  return 'An unexpected error occurred'
}

/**
 * Format file name with extension highlighting
 */
export function formatFileName(filename: string): { name: string; extension: string } {
  const lastDotIndex = filename.lastIndexOf('.')
  if (lastDotIndex === -1) {
    return { name: filename, extension: '' }
  }

  return {
    name: filename.slice(0, lastDotIndex),
    extension: filename.slice(lastDotIndex),
  }
}

/**
 * Format MIME type to human readable string
 */
export function formatMimeType(mimeType: string): string {
  const mimeTypeMap: Record<string, string> = {
    'application/pdf': 'PDF Document',
    'application/msword': 'Word Document',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'Word Document',
    'application/vnd.ms-excel': 'Excel Spreadsheet',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'Excel Spreadsheet',
    'application/vnd.ms-powerpoint': 'PowerPoint Presentation',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'PowerPoint Presentation',
    'text/plain': 'Text File',
    'text/markdown': 'Markdown File',
    'image/jpeg': 'JPEG Image',
    'image/png': 'PNG Image',
    'image/gif': 'GIF Image',
    'image/webp': 'WebP Image',
    'audio/mpeg': 'MP3 Audio',
    'audio/wav': 'WAV Audio',
    'video/mp4': 'MP4 Video',
    'video/quicktime': 'QuickTime Video',
    'application/json': 'JSON File',
    'text/csv': 'CSV File',
    'application/xml': 'XML File',
    'text/html': 'HTML File',
  }

  return mimeTypeMap[mimeType] || mimeType.replace(/\//g, ' ').replace(/(^|\s)\w/g, l => l.toUpperCase())
}

/**
 * Format priority level to display text
 */
export function formatPriority(priority: 'low' | 'normal' | 'high' | 'urgent'): string {
  const priorityMap = {
    low: 'Low Priority',
    normal: 'Normal Priority',
    high: 'High Priority',
    urgent: 'Urgent Priority',
  }

  return priorityMap[priority] || priority
}

/**
 * Format status to display text
 */
export function formatStatus(status: string): string {
  return status
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}