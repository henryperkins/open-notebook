/**
 * React Hook for Enriched References
 *
 * This hook provides a simple way to enhance references with human-readable titles
 * while handling loading states, caching, and error recovery.
 */

import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { toast } from 'sonner'
import {
  augmentReferencesWithTitles,
  ReferenceMetadataMap,
  AugmentedReferenceData,
  createMetadataAwareLinkComponent,
  MetadataLinkComponent
} from '@/lib/utils/reference-metadata'
import { ReferenceType, convertReferencesToCompactMarkdown } from '@/lib/utils/source-references'

interface UseEnrichedReferencesOptions {
  enableAugmentation?: boolean
  onReferenceClick?: (type: ReferenceType, id: string) => void
  showToastOnError?: boolean
}

interface UseEnrichedReferencesReturn {
  // Synchronous data (immediately available)
  processedText: string
  isEnriched: boolean

  // Asynchronous data (fetched)
  enrichedData: AugmentedReferenceData[] | null
  metadata: ReferenceMetadataMap
  isLoading: boolean
  error: string | null

  // Utilities
  LinkComponent: MetadataLinkComponent
  refreshMetadata: () => Promise<void>

  // Internal state for debugging
  hasReferences: boolean
  referenceCount: number
}

/**
 * Hook to enrich references with metadata
 *
 * @param text - Text containing references to enrich
 * @param options - Configuration options
 * @returns Object with enriched data and utilities
 */
export function useEnrichedReferences(
  text: string,
  options: UseEnrichedReferencesOptions = {}
): UseEnrichedReferencesReturn {
  const {
    enableAugmentation = true,
    onReferenceClick,
    showToastOnError = true
  } = options

  // State management
  const [processedText, setProcessedText] = useState<string>('')
  const [enrichedData, setEnrichedData] = useState<AugmentedReferenceData[] | null>(null)
  const [metadata, setMetadata] = useState<ReferenceMetadataMap>({})
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  // Refs to avoid stale closures
  const textRef = useRef(text)
  const optionsRef = useRef(options)
  const metadataRef = useRef<ReferenceMetadataMap>({})
  const abortControllerRef = useRef<AbortController | null>(null)

  // Update refs when props change
  useEffect(() => {
    textRef.current = text
    optionsRef.current = options
  }, [text, options])

  /**
   * Process text immediately (synchronous)
   */
  const processTextImmediate = useCallback((inputText: string) => {
    try {
      const processed = convertReferencesToCompactMarkdown(inputText)
      setProcessedText(processed)
      return processed
    } catch (err) {
      console.error('Failed to process text immediately:', err)
      setProcessedText(inputText)
      return inputText
    }
  }, [])

  /**
   * Enrich references with metadata (asynchronous)
   */
  const enrichReferences = useCallback(async (inputText: string) => {
    if (!enableAugmentation || !inputText.trim()) {
      setEnrichedData(null)
      setMetadata({})
      metadataRef.current = {}
      setIsLoading(false)
      setError(null)
      return
    }

    // Cancel any existing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }

    // Create new abort controller
    abortControllerRef.current = new AbortController()

    setIsLoading(true)
    setError(null)

    try {
      const result = await augmentReferencesWithTitles(inputText, {
        fetchMetadata: true,
        existingMetadata: metadataRef.current // Use existing metadata as base
      })

      // Check if request was aborted
      if (abortControllerRef.current?.signal.aborted) {
        return
      }

      setEnrichedData(result.augmentedData)
      setMetadata(result.metadata)
      metadataRef.current = result.metadata

    } catch (err) {
      // Don't show error for aborted requests
      if (abortControllerRef.current?.signal.aborted) {
        return
      }

      console.error('Failed to enrich references:', err)
      const errorMessage = err instanceof Error ? err.message : 'Failed to load reference metadata'
      setError(errorMessage)

      if (showToastOnError) {
        toast.error('Could not load reference titles')
      }

      // Set fallback data
      setEnrichedData(null)

    } finally {
      setIsLoading(false)
      abortControllerRef.current = null
    }
  }, [enableAugmentation, showToastOnError])

  /**
   * Refresh metadata for current references
   */
  const refreshMetadata = useCallback(async () => {
    await enrichReferences(textRef.current)
  }, [enrichReferences])

  /**
   * Create metadata-aware link component
   */
  const LinkComponent = useMemo(
    () =>
      createMetadataAwareLinkComponent(
        (type: ReferenceType, id: string) => {
          onReferenceClick?.(type, id)
        },
        metadata
      ),
    [onReferenceClick, metadata]
  )

  // Process text immediately when it changes
  useEffect(() => {
    processTextImmediate(text)
  }, [text, processTextImmediate])

  // Enrich references when text or options change
  useEffect(() => {
    enrichReferences(text)
  }, [text, enrichReferences])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [])

  // Calculate reference information
  const hasReferences = processedText.includes('#ref-')
  const referenceCount = enrichedData?.length || 0
  const isEnriched = enrichedData !== null

  return {
    // Synchronous data
    processedText,
    isEnriched,

    // Asynchronous data
    enrichedData,
    metadata,
    isLoading,
    error,

    // Utilities
    LinkComponent,
    refreshMetadata,

    // Debug info
    hasReferences,
    referenceCount
  }
}

/**
 * Hook for streaming responses that defers enrichment until streaming is complete
 */
export function useStreamingEnrichedReferences(
  text: string,
  isStreaming: boolean,
  options: UseEnrichedReferencesOptions = {}
) {
  const {
    enrichedData,
    metadata,
    isLoading,
    error,
    LinkComponent,
    refreshMetadata,
    ...rest
  } = useEnrichedReferences(text, {
    ...options,
    enableAugmentation: (options.enableAugmentation ?? true) && !isStreaming // Only enrich when not streaming
  })

  return {
    enrichedData,
    metadata,
    isLoading,
    error,
    LinkComponent,
    refreshMetadata,
    isStreaming,
    ...rest
  }
}
