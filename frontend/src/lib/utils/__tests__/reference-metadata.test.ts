/**
 * Test file for reference metadata augmentation system
 */

import {
  fetchMultipleReferenceMetadata,
  augmentReferencesWithTitles,
  extractUniqueReferences,
  generateFallbackTitle,
  ReferenceType
} from '../reference-metadata'

// Mock the API functions
jest.mock('@/lib/api/sources', () => ({
  sourcesApi: {
    get: jest.fn()
  }
}))

jest.mock('@/lib/api/notes', () => ({
  notesApi: {
    get: jest.fn()
  }
}))

jest.mock('@/lib/api/insights', () => ({
  insightsApi: {
    get: jest.fn()
  }
}))

// Mock the source-references functions
jest.mock('../source-references', () => ({
  parseSourceReferences: jest.fn(),
  convertReferencesToCompactMarkdown: jest.fn()
}))

import { sourcesApi, notesApi, insightsApi } from '@/lib/api/sources'
import { parseSourceReferences, convertReferencesToCompactMarkdown } from '../source-references'

describe('Reference Metadata System', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('generateFallbackTitle', () => {
    it('should generate appropriate fallback titles', () => {
      expect(generateFallbackTitle('source', 'abc123def456'))
        .toBe('Source abc123de...')

      expect(generateFallbackTitle('note', 'fed789cba012'))
        .toBe('Note fed789cb...')

      expect(generateFallbackTitle('source_insight', 'b345c678d901'))
        .toBe('Insight b345c67...')
    })
  })

  describe('extractUniqueReferences', () => {
    it('should extract unique references from text', () => {
      const mockReferences = [
        { type: 'source' as ReferenceType, id: 'abc123', startIndex: 0, endIndex: 11, originalText: 'source:abc123' },
        { type: 'note' as ReferenceType, id: 'def456', startIndex: 15, endIndex: 25, originalText: 'note:def456' },
        { type: 'source' as ReferenceType, id: 'abc123', startIndex: 30, endIndex: 41, originalText: 'source:abc123' } // Duplicate
      ]

      ;(parseSourceReferences as jest.Mock).mockReturnValue(mockReferences)

      const result = extractUniqueReferences('Test source:abc123 and note:def456 and source:abc123')

      expect(result).toEqual([
        { type: 'source', id: 'abc123' },
        { type: 'note', id: 'def456' }
      ])

      expect(parseSourceReferences).toHaveBeenCalledWith('Test source:abc123 and note:def456 and source:abc123')
    })
  })

  describe('fetchMultipleReferenceMetadata', () => {
    it('should fetch metadata for multiple references in parallel', async () => {
      const references = [
        { type: 'source' as ReferenceType, id: 'source1' },
        { type: 'note' as ReferenceType, id: 'note1' },
        { type: 'source_insight' as ReferenceType, id: 'insight1' }
      ]

      const mockSourceData = { id: 'source1', title: 'Test Source' }
      const mockNoteData = { id: 'note1', title: 'Test Note' }
      const mockInsightData = { id: 'insight1', insight_type: 'summary', content: 'Test insight' }

      ;(sourcesApi.get as jest.Mock).mockResolvedValue(mockSourceData)
      ;(notesApi.get as jest.Mock).mockResolvedValue(mockNoteData)
      ;(insightsApi.get as jest.Mock).mockResolvedValue(mockInsightData)

      const result = await fetchMultipleReferenceMetadata(references)

      expect(sourcesApi.get).toHaveBeenCalledWith('source1')
      expect(notesApi.get).toHaveBeenCalledWith('note1')
      expect(insightsApi.get).toHaveBeenCalledWith('insight1')

      expect(result).toEqual({
        'source:source1': {
          id: 'source1',
          type: 'source',
          title: 'Test Source',
          fallbackTitle: 'Source source1...'
        },
        'note:note1': {
          id: 'note1',
          type: 'note',
          title: 'Test Note',
          fallbackTitle: 'Note note1...'
        },
        'source_insight:insight1': {
          id: 'insight1',
          type: 'source_insight',
          title: 'Insight from insight1...',
          fallbackTitle: 'Insight insight1...'
        }
      })
    })

    it('should handle API errors gracefully', async () => {
      const references = [
        { type: 'source' as ReferenceType, id: 'nonexistent' }
      ]

      ;(sourcesApi.get as jest.Mock).mockRejectedValue(new Error('Not found'))

      const result = await fetchMultipleReferenceMetadata(references)

      expect(result).toEqual({
        'source:nonexistent': {
          id: 'nonexistent',
          type: 'source',
          title: null,
          fallbackTitle: 'Source nonexist...'
        }
      })
    })
  })

  describe('augmentReferencesWithTitles', () => {
    it('should augment references with metadata', async () => {
      const text = 'Test content with source:abc123 and note:def456'
      const compactText = 'Test content with [1](#ref-source-abc123) and [2](#ref-note-def456)\n\n**References:**\n[1] [Source: abc123](#ref-source-abc123)\n[2] [Note: def456](#ref-note-def456)'

      const mockReferences = [
        { type: 'source' as ReferenceType, id: 'abc123', startIndex: 20, endIndex: 33, originalText: 'source:abc123' },
        { type: 'note' as ReferenceType, id: 'def456', startIndex: 38, endIndex: 49, originalText: 'note:def456' }
      ]

      ;(parseSourceReferences as jest.Mock).mockReturnValue(mockReferences)
      ;(convertReferencesToCompactMarkdown as jest.Mock).mockReturnValue(compactText)

      const mockMetadata = {
        'source:abc123': {
          id: 'abc123',
          type: 'source' as ReferenceType,
          title: 'Test Source Title',
          fallbackTitle: 'Source abc123...'
        },
        'note:def456': {
          id: 'def456',
          type: 'note' as ReferenceType,
          title: 'Test Note Title',
          fallbackTitle: 'Note def456...'
        }
      }

      // Mock the internal fetch function
      const mockFetchMultipleReferenceMetadata = jest.fn().mockResolvedValue(mockMetadata)
      jest.doMock('../reference-metadata', () => ({
        ...jest.requireActual('../reference-metadata'),
        fetchMultipleReferenceMetadata: mockFetchMultipleReferenceMetadata
      }))

      const result = await augmentReferencesWithTitles(text, { fetchMetadata: true })

      expect(result).toEqual({
        text: compactText,
        metadata: mockMetadata,
        augmentedData: [
          {
            number: 1,
            type: 'source',
            id: 'abc123',
            title: 'Test Source Title',
            displayLabel: 'Test Source Title'
          },
          {
            number: 2,
            type: 'note',
            id: 'def456',
            title: 'Test Note Title',
            displayLabel: 'Test Note Title'
          }
        ]
      })
    })

    it('should use fallback titles when metadata is unavailable', async () => {
      const text = 'Test content with source:abc123'
      const compactText = 'Test content with [1](#ref-source-abc123)\n\n**References:**\n[1] [Source: abc123](#ref-source-abc123)'

      const mockReferences = [
        { type: 'source' as ReferenceType, id: 'abc123', startIndex: 20, endIndex: 33, originalText: 'source:abc123' }
      ]

      ;(parseSourceReferences as jest.Mock).mockReturnValue(mockReferences)
      ;(convertReferencesToCompactMarkdown as jest.Mock).mockReturnValue(compactText)

      const mockMetadata = {
        'source:abc123': {
          id: 'abc123',
          type: 'source' as ReferenceType,
          title: null, // No title available
          fallbackTitle: 'Source abc123...'
        }
      }

      const mockFetchMultipleReferenceMetadata = jest.fn().mockResolvedValue(mockMetadata)
      jest.doMock('../reference-metadata', () => ({
        ...jest.requireActual('../reference-metadata'),
        fetchMultipleReferenceMetadata: mockFetchMultipleReferenceMetadata
      }))

      const result = await augmentReferencesWithTitles(text, { fetchMetadata: true })

      expect(result.augmentedData).toEqual([
        {
          number: 1,
          type: 'source',
          id: 'abc123',
          title: null,
          displayLabel: 'Source abc123...' // Uses fallback
        }
      ])
    })
  })
})