# Enhanced References System Documentation

## Overview

The Enhanced References System adds human-readable titles to reference citations, significantly improving the user experience by replacing cryptic IDs with meaningful labels. The system maintains backwards compatibility while providing rich metadata for references.

## Problem Solved

Previously, reference lists showed only IDs:
```
References:
[1] Source: abc123def456
[2] Note: fed789cba012
[3] Insight: b345c678d901
```

Now they display meaningful titles:
```
References:
[1] Source: Machine Learning Fundamentals
[2] Note: Research Notes on RAG Systems
[3] Insight: Key Takeaways from Document Analysis
```

## Architecture

### Layered Design

The system uses a layered approach that maintains backwards compatibility:

1. **Core Layer** (`source-references.ts`) - Existing synchronous parsing
2. **Augmentation Layer** (`reference-metadata.ts`) - Async metadata fetching
3. **Hook Layer** (`use-enriched-references.ts`) - React integration
4. **UI Layer** (`EnrichedReferencesList.tsx`) - Enhanced display components

### Key Features

- **Async Enhancement**: Fetches metadata without blocking initial render
- **Intelligent Caching**: Avoids duplicate API calls for repeated references
- **Graceful Degradation**: Falls back to IDs when metadata unavailable
- **Streaming Support**: Defers enrichment until streaming completes
- **Error Recovery**: Handles API failures gracefully

## Usage

### Basic Hook Usage

```typescript
import { useEnrichedReferences } from '@/lib/hooks/use-enriched-references'

function MyComponent({ content }) {
  const {
    processedText,      // Text with numbered citations
    enrichedData,       // Array of reference data with titles
    isLoading,          // Loading state for metadata
    error,              // Any error that occurred
    LinkComponent,      // Enhanced link component
    refreshMetadata,    // Function to refresh metadata
    hasReferences,      // Boolean indicating if references exist
    referenceCount      // Number of references found
  } = useEnrichedReferences(content, {
    enableAugmentation: true,
    onReferenceClick: handleReferenceClick
  })

  return (
    <div>
      <ReactMarkdown components={{ a: LinkComponent }}>
        {processedText}
      </ReactMarkdown>

      {hasReferences && (
        <EnrichedReferencesList
          references={enrichedData || []}
          isLoading={isLoading}
          error={error}
          onReferenceClick={handleReferenceClick}
          onRefresh={refreshMetadata}
        />
      )}
    </div>
  )
}
```

### Streaming Usage

```typescript
import { useStreamingEnrichedReferences } from '@/lib/hooks/use-enriched-references'

function StreamingComponent({ content, isStreaming }) {
  const { processedText, enrichedData, isLoading, isStreaming } =
    useStreamingEnrichedReferences(content, isStreaming)

  // Metadata is only fetched when isStreaming is false
  return (
    <div>
      <ReactMarkdown>{processedText}</ReactMarkdown>

      {!isStreaming && hasReferences && (
        <EnrichedReferencesList references={enrichedData} />
      )}
    </div>
  )
}
```

### Direct API Usage

```typescript
import { augmentReferencesWithTitles } from '@/lib/utils/reference-metadata'

async function enhanceReferences(text: string) {
  const result = await augmentReferencesWithTitles(text, {
    fetchMetadata: true
  })

  console.log(result.text)           // Text with numbered citations
  console.log(result.metadata)       // Metadata map
  console.log(result.augmentedData)  // Array of reference data

  return result
}
```

## Components

### EnrichedReferencesList

Displays references with rich formatting and metadata:

```typescript
<EnrichedReferencesList
  references={enrichedData}
  isLoading={isLoading}
  error={error}
  onReferenceClick={handleReferenceClick}
  onRefresh={refreshMetadata}
  compact={false}  // Use compact mode for tight spaces
/>
```

**Props:**
- `references`: Array of `AugmentedReferenceData`
- `isLoading`: Show loading state
- `error`: Error message to display
- `onReferenceClick`: Click handler for references
- `onRefresh`: Function to retry failed requests
- `compact`: Use compact layout
- `className`: Additional CSS classes

## Data Structures

### ReferenceMetadata

```typescript
interface ReferenceMetadata {
  id: string                    // Original reference ID
  type: ReferenceType          // 'source' | 'note' | 'source_insight'
  title: string | null         // Fetched title or null
  fallbackTitle: string        // Generated fallback label
}
```

### AugmentedReferenceData

```typescript
interface AugmentedReferenceData {
  number: number               // Citation number [1], [2], etc.
  type: ReferenceType          // Reference type
  id: string                   // Original ID
  title: string | null         // Fetched title
  displayLabel: string         // Human-friendly label
}
```

## Caching Strategy

### Memory Caching

- **In-memory cache**: `Map<string, ReferenceMetadata>`
- **Deduplication**: Prevents duplicate API calls
- **Automatic cleanup**: Cache persists for session duration

### Request Deduplication

- **Pending requests**: `Map<string, Promise<ReferenceMetadata>>`
- **Race condition prevention**: Multiple components requesting same reference
- **Automatic cleanup**: Removes completed requests

### Error Caching

- **Failed requests**: Cached with fallback data
- **Prevents retry loops**: Won't retry failed requests in same session
- **Graceful degradation**: Uses generated labels when API fails

## Performance Considerations

### Optimization Techniques

1. **Lazy Loading**: Metadata fetched only when needed
2. **Parallel Requests**: Multiple references fetched simultaneously
3. **Request Cancellation**: Abort controllers for cleanup
4. **Incremental Updates**: Reuse existing metadata when possible

### Streaming Optimization

- **Deferred Fetching**: Waits until streaming completes
- **Progressive Enhancement**: Shows basic citations immediately
- **Background Loading**: Fetches metadata without blocking UI

## API Integration

### Supported Endpoints

- **Sources**: `sourcesApi.get(id)` → returns `SourceDetailResponse`
- **Notes**: `notesApi.get(id)` → returns `NoteResponse`
- **Insights**: `insightsApi.get(id)` → returns `SourceInsightResponse`

### Error Handling

- **Network Errors**: Graceful fallback to ID-based labels
- **Not Found Errors**: Generate descriptive fallback titles
- **Rate Limiting**: Automatic retry with exponential backoff
- **Timeout Handling**: Cancel long-running requests

## Migration Guide

### From Basic References

**Before:**
```typescript
const LinkComponent = createReferenceLinkComponent(onClick)
<ReactMarkdown components={{ a: LinkComponent }}>
  {convertReferencesToCompactMarkdown(content)}
</ReactMarkdown>
```

**After:**
```typescript
const { processedText, LinkComponent, enrichedData } =
  useEnrichedReferences(content)

<ReactMarkdown components={{ a: LinkComponent }}>
  {processedText}
</ReactMarkdown>
<EnrichedReferencesList references={enrichedData} />
```

### Backwards Compatibility

The existing `convertReferencesToCompactMarkdown` function remains unchanged and continues to work for synchronous use cases.

## Configuration Options

### Hook Options

```typescript
interface UseEnrichedReferencesOptions {
  enableAugmentation?: boolean    // Enable metadata fetching
  onReferenceClick?: Function     // Reference click handler
  showToastOnError?: boolean      // Show error toast notifications
}
```

### Augmentation Options

```typescript
interface AugmentReferencesOptions {
  fetchMetadata?: boolean         // Whether to fetch metadata
  existingMetadata?: ReferenceMetadataMap  // Pre-existing metadata
}
```

## Testing

### Unit Tests

- **Metadata fetching**: Test API integration and caching
- **Hook behavior**: Test state management and lifecycle
- **Error scenarios**: Test graceful degradation
- **Performance**: Test caching and deduplication

### Integration Tests

- **End-to-end flow**: From raw text to enriched display
- **User interactions**: Click handlers and refresh functionality
- **Streaming scenarios**: Proper deferring during streaming
- **Error recovery**: Retry mechanisms and fallback behavior

## Future Enhancements

### Planned Features

1. **Prefetching**: Load metadata for likely references
2. **Batch API**: Single endpoint for multiple references
3. **Local Storage**: Persist cache across sessions
4. **Smart Refresh**: Update only stale metadata
5. **Advanced Caching**: TTL-based cache invalidation

### API Improvements

1. **Metadata Endpoint**: Dedicated endpoint for reference metadata
2. **Batch Requests**: Fetch multiple references in single request
3. **Partial Responses**: Return only needed fields
4. **Error Details**: Better error information for debugging

## Troubleshooting

### Common Issues

**References not enriching:**
- Check `enableAugmentation: true` in hook options
- Verify API endpoints are accessible
- Check network connectivity

**Duplicate API calls:**
- Verify caching is working properly
- Check component key props for proper re-rendering

**Slow loading:**
- Consider enabling `compact` mode for better UX
- Check API response times
- Monitor network requests

**Missing titles:**
- Verify sources have titles set in the database
- Check insight generation includes meaningful descriptions
- Fallback titles will be generated automatically