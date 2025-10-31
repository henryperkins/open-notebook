/**
 * Reference Metadata Augmentation System
 *
 * This system enhances reference IDs with human-readable titles by fetching metadata
 * from the API. It maintains backwards compatibility while providing richer UI labels.
 */

import type { AnchorHTMLAttributes, ReactNode, FC } from 'react'
import { sourcesApi } from '@/lib/api/sources'
import { notesApi } from '@/lib/api/notes'
import { insightsApi } from '@/lib/api/insights'
import { ReferenceType, parseSourceReferences, convertReferencesToCompactMarkdown } from './source-references'

export interface ReferenceMetadata {
  id: string
  type: ReferenceType
  title: string | null
  fallbackTitle: string // Generated from type and ID when title is null
}

export interface ReferenceMetadataMap {
  [key: string]: ReferenceMetadata // key format: "type:id"
}

export interface AugmentedReferenceData {
  number: number
  type: ReferenceType
  id: string
  title: string | null
  displayLabel: string // Human-friendly label
}

// Cache for reference metadata to avoid duplicate API calls
const metadataCache = new Map<string, ReferenceMetadata>()
const pendingRequests = new Map<string, Promise<ReferenceMetadata>>()

/**
 * Generate a fallback title when API data is not available
 */
export function generateFallbackTitle(type: ReferenceType, id: string): string {
  const typeLabels: Record<ReferenceType, string> = {
    source: 'Source',
    note: 'Note',
    source_insight: 'Insight'
  }
  return `${typeLabels[type]} ${id.slice(0, 8)}...`
}

/**
 * Fetch metadata for a single reference
 */
async function fetchReferenceMetadata(type: ReferenceType, id: string): Promise<ReferenceMetadata> {
  const cacheKey = `${type}:${id}`

  // Check cache first
  if (metadataCache.has(cacheKey)) {
    return metadataCache.get(cacheKey)!
  }

  // Check if request is already in flight
  if (pendingRequests.has(cacheKey)) {
    return pendingRequests.get(cacheKey)!
  }

  // Create the fetch promise
  const fetchPromise = (async (): Promise<ReferenceMetadata> => {
    try {
      let title: string | null = null

      switch (type) {
        case 'source':
          const sourceData = await sourcesApi.get(id)
          title = sourceData.title
          break

        case 'note':
          const noteData = await notesApi.get(id)
          title = noteData.title
          break

        case 'source_insight':
          await insightsApi.get(id)
          // Insights don't have titles, so we'll create a descriptive one
          title = `Insight from ${id.slice(0, 8)}...`
          break

        default:
          console.warn(`Unknown reference type: ${type}`)
      }

      const metadata: ReferenceMetadata = {
        id,
        type,
        title,
        fallbackTitle: generateFallbackTitle(type, id)
      }

      // Cache the result
      metadataCache.set(cacheKey, metadata)
      return metadata

    } catch (error) {
      console.warn(`Failed to fetch metadata for ${type}:${id}`, error)

      // Create fallback metadata
      const fallbackMetadata: ReferenceMetadata = {
        id,
        type,
        title: null,
        fallbackTitle: generateFallbackTitle(type, id)
      }

      // Cache the fallback result to avoid retrying failed requests
      metadataCache.set(cacheKey, fallbackMetadata)
      return fallbackMetadata

    } finally {
      // Clean up pending request
      pendingRequests.delete(cacheKey)
    }
  })()

  // Store the pending request
  pendingRequests.set(cacheKey, fetchPromise)

  return fetchPromise
}

/**
 * Fetch metadata for multiple references in parallel
 */
export async function fetchMultipleReferenceMetadata(
  references: Array<{ type: ReferenceType; id: string }>
): Promise<ReferenceMetadataMap> {
  // Group references by type for potential batching optimizations
  const uniqueReferences = Array.from(
    new Set(references.map(ref => `${ref.type}:${ref.id}`))
  ).map(key => {
    const [type, id] = key.split(':') as [ReferenceType, string]
    return { type, id }
  })

  // Fetch all metadata in parallel
  const metadataPromises = uniqueReferences.map(ref =>
    fetchReferenceMetadata(ref.type, ref.id)
  )

  const metadataResults = await Promise.all(metadataPromises)

  // Convert to map
  const metadataMap: ReferenceMetadataMap = {}
  metadataResults.forEach(metadata => {
    metadataMap[`${metadata.type}:${metadata.id}`] = metadata
  })

  return metadataMap
}

/**
 * Extract unique references from text using the existing parser
 */
export function extractUniqueReferences(text: string): Array<{ type: ReferenceType; id: string }> {
  const references = parseSourceReferences(text)
  const uniqueRefs = new Map<string, { type: ReferenceType; id: string }>()

  references.forEach(ref => {
    const key = `${ref.type}:${ref.id}`
    if (!uniqueRefs.has(key)) {
      uniqueRefs.set(key, { type: ref.type, id: ref.id })
    }
  })

  return Array.from(uniqueRefs.values())
}

/**
 * Augment references with human-friendly titles
 *
 * This is the main function that enriches the reference data with metadata.
 * It's designed to be used client-side where async operations are acceptable.
 */
export async function augmentReferencesWithTitles(
  text: string,
  options: {
    fetchMetadata?: boolean
    existingMetadata?: ReferenceMetadataMap
  } = {}
): Promise<{
  text: string // Text with compact markdown references
  metadata: ReferenceMetadataMap
  augmentedData: AugmentedReferenceData[]
}> {
  const { fetchMetadata = true, existingMetadata = {} } = options

  // First, convert references to compact markdown (existing synchronous logic)
  const compactText = convertReferencesToCompactMarkdown(text)

  // Extract unique references from the original text
  const uniqueReferences = extractUniqueReferences(text)

  // Fetch metadata if requested
  let metadataMap = { ...existingMetadata }

  if (fetchMetadata && uniqueReferences.length > 0) {
    const newMetadata = await fetchMultipleReferenceMetadata(uniqueReferences)
    metadataMap = { ...metadataMap, ...newMetadata }
  }

  // Build augmented reference data for the references section
  // We need to parse the compact text to get the numbered citations
  const compactReferences = parseSourceReferences(compactText)
  const augmentedData: AugmentedReferenceData[] = []

  // Create a map to track which references have been processed
  const processedRefs = new Map<string, number>()
  let nextNumber = 1

  compactReferences.forEach(ref => {
    const key = `${ref.type}:${ref.id}`

    if (!processedRefs.has(key)) {
      const metadata = metadataMap[key]
      const displayLabel = metadata?.title || metadata?.fallbackTitle || `${ref.type}:${ref.id}`

      augmentedData.push({
        number: nextNumber,
        type: ref.type,
        id: ref.id,
        title: metadata?.title || null,
        displayLabel
      })

      processedRefs.set(key, nextNumber)
      nextNumber++
    }
  })

  // Rebuild the reference list with enriched titles to ensure it's part of the final markdown
  let finalText = compactText
  if (augmentedData.length > 0) {
    const refListLines: string[] = ['\n\n**References:**']
    const sortedData = [...augmentedData].sort((a, b) => a.number - b.number)

    for (const refData of sortedData) {
      const refListItem = `[${refData.number}] [${refData.displayLabel}](#ref-${refData.type}-${refData.id})`
      refListLines.push(refListItem)
    }

    // Replace the original reference list (which only has IDs) with the new one
    const oldRefListRegex = /\n\n\*\*References:\*\*[\s\S]*/
    if (oldRefListRegex.test(compactText)) {
      finalText = compactText.replace(oldRefListRegex, refListLines.join('  \n'))
    } else {
      // This case should not happen if compactText was generated correctly, but as a fallback
      finalText = compactText + refListLines.join('  \n')
    }
  }

  return {
    text: finalText,
    metadata: metadataMap,
    augmentedData
  }
}

/**
 * Create a reference link component that uses metadata for display
 */
export type MetadataLinkComponentProps = AnchorHTMLAttributes<HTMLAnchorElement> & {
  children?: ReactNode
}

export type MetadataLinkComponent = FC<MetadataLinkComponentProps>

export function createMetadataAwareLinkComponent(
  onReferenceClick: (type: ReferenceType, id: string) => void,
  metadataMap: ReferenceMetadataMap = {}
) : MetadataLinkComponent {
  const MetadataAwareLinkComponent: MetadataLinkComponent = ({
    href,
    children,
    ...props
  }) => {
    // Check if this is a reference link
    if (href?.startsWith('#ref-')) {
      const parts = href.substring(5).split('-')
      const type = parts[0] as ReferenceType
      const id = parts.slice(1).join('-')

      const metadata = metadataMap[`${type}:${id}`]
      const displayLabel = metadata?.title || metadata?.fallbackTitle || children

      return (
        <button
          onClick={(e) => {
            e.preventDefault()
            e.stopPropagation()
            onReferenceClick(type, id)
          }}
          className="text-primary hover:underline cursor-pointer inline font-medium"
          type="button"
          title={`View ${displayLabel}`}
        >
          {children}
        </button>
      )
    }

    // Regular link
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" {...props} className="text-primary hover:underline">
        {children}
      </a>
    )
  }

  MetadataAwareLinkComponent.displayName = 'MetadataAwareLinkComponent'
  return MetadataAwareLinkComponent
}
