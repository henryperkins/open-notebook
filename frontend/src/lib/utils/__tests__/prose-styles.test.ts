/**
 * Test file for prose styles utility
 * This file verifies that the standardized prose styling works correctly
 */

import { getProseClasses, getProseStyle, PROSE_STYLES } from '../prose-styles'

describe('Prose Styles', () => {
  describe('getProseClasses', () => {
    it('should return default classes when no options provided', () => {
      const classes = getProseClasses()
      expect(classes).toContain('prose')
      expect(classes).toContain('prose-sm')
      expect(classes).toContain('prose-neutral')
      expect(classes).toContain('dark:prose-invert')
      expect(classes).toContain('max-w-none')
    })

    it('should include size class when specified', () => {
      const classes = getProseClasses({ size: 'lg' })
      expect(classes).toContain('prose-lg')
      expect(classes).not.toContain('prose-sm')
    })

    it('should include variant class when specified', () => {
      const classes = getProseClasses({ variant: 'default' })
      expect(classes).toContain('prose')
      expect(classes).not.toContain('prose-neutral')
    })

    it('should not include max-w-none when maxWidth is true', () => {
      const classes = getProseClasses({ maxWidth: true })
      expect(classes).not.toContain('max-w-none')
    })

    it('should include custom classes when provided', () => {
      const classes = getProseClasses({ customClasses: 'custom-class another-class' })
      expect(classes).toContain('custom-class')
      expect(classes).toContain('another-class')
    })

    it('should include enhanced styling classes', () => {
      const classes = getProseClasses()
      expect(classes).toContain('prose-a:text-blue-600')
      expect(classes).toContain('prose-headings:font-semibold')
      expect(classes).toContain('prose-p:mb-4')
      expect(classes).toContain('prose-code:bg-muted')
      expect(classes).toContain('prose-blockquote:border-l-4')
    })
  })

  describe('PROSE_STYLES', () => {
    it('should provide predefined styles for common use cases', () => {
      const defaultStyle = PROSE_STYLES.DEFAULT()
      expect(defaultStyle).toContain('prose-sm')
      expect(defaultStyle).toContain('prose-neutral')

      const streamingStyle = PROSE_STYLES.STREAMING()
      expect(streamingStyle).toContain('prose-sm')
      expect(streamingStyle).toContain('prose-p:leading-relaxed')

      const sourceStyle = PROSE_STYLES.SOURCE()
      expect(sourceStyle).toContain('prose-sm')
      expect(sourceStyle).toContain('prose-neutral')

      const documentStyle = PROSE_STYLES.DOCUMENT()
      expect(documentStyle).toContain('prose-base')

      const compactStyle = PROSE_STYLES.COMPACT()
      expect(compactStyle).toContain('prose-xs')
      expect(compactStyle).toContain('prose-p:mb-2')
    })
  })

  describe('getProseStyle', () => {
    it('should return appropriate style for each context', () => {
      expect(getProseStyle('chat')).toBe(PROSE_STYLES.DEFAULT())
      expect(getProseStyle('streaming')).toBe(PROSE_STYLES.STREAMING())
      expect(getProseStyle('source')).toBe(PROSE_STYLES.SOURCE())
      expect(getProseStyle('document')).toBe(PROSE_STYLES.DOCUMENT())
      expect(getProseStyle('compact')).toBe(PROSE_STYLES.COMPACT())
    })

    it('should return default style for unknown context', () => {
      const defaultStyle = PROSE_STYLES.DEFAULT()
      const unknownStyle = getProseStyle('unknown' as unknown as 'chat')
      expect(unknownStyle).toBe(defaultStyle)
    })
  })
})
