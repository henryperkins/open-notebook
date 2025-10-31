/**
 * Enhanced References List Component
 *
 * Displays references with human-readable titles and provides better UX
 * compared to the basic numbered list.
 */

import React from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  FileText,
  Lightbulb,
  FileEdit,
  ExternalLink,
  Loader2,
  RefreshCw,
  AlertCircle
} from 'lucide-react'
import { AugmentedReferenceData } from '@/lib/utils/reference-metadata'
import { ReferenceType } from '@/lib/utils/source-references'

interface EnrichedReferencesListProps {
  references: AugmentedReferenceData[]
  isLoading?: boolean
  error?: string | null
  onReferenceClick?: (type: ReferenceType, id: string) => void
  onRefresh?: () => void
  className?: string
  compact?: boolean
}

/**
 * Get icon for reference type
 */
function getReferenceIcon(type: ReferenceType) {
  switch (type) {
    case 'source':
      return FileText
    case 'note':
      return FileEdit
    case 'source_insight':
      return Lightbulb
    default:
      return FileText
  }
}

/**
 * Get color scheme for reference type
 */
function getReferenceColor(type: ReferenceType) {
  switch (type) {
    case 'source':
      return 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-800'
    case 'note':
      return 'bg-green-50 text-green-700 border-green-200 dark:bg-green-950 dark:text-green-300 dark:border-green-800'
    case 'source_insight':
      return 'bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950 dark:text-purple-300 dark:border-purple-800'
    default:
      return 'bg-gray-50 text-gray-700 border-gray-200 dark:bg-gray-950 dark:text-gray-300 dark:border-gray-800'
  }
}

/**
 * Get human-readable type label
 */
function getTypeLabel(type: ReferenceType): string {
  switch (type) {
    case 'source':
      return 'Source'
    case 'note':
      return 'Note'
    case 'source_insight':
      return 'Insight'
    default:
      return 'Document'
  }
}

/**
 * Individual reference item
 */
function ReferenceItem({
  reference,
  onClick
}: {
  reference: AugmentedReferenceData
  onClick?: () => void
}) {
  const IconComponent = getReferenceIcon(reference.type)
  const colorClass = getReferenceColor(reference.type)
  const typeLabel = getTypeLabel(reference.type)

  return (
    <div className="flex items-start gap-3 p-3 rounded-lg border bg-card hover:bg-muted/50 transition-colors">
      {/* Reference number */}
      <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary text-primary-foreground text-xs font-medium flex items-center justify-center">
        {reference.number}
      </div>

      {/* Reference content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <Badge variant="outline" className={`text-xs ${colorClass}`}>
            <IconComponent className="h-3 w-3 mr-1" />
            {typeLabel}
          </Badge>
          {onClick && (
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-xs"
              onClick={onClick}
            >
              <ExternalLink className="h-3 w-3 mr-1" />
              View
            </Button>
          )}
        </div>

        <div className="text-sm font-medium text-foreground leading-tight">
          {reference.displayLabel}
        </div>

        {reference.title && reference.title !== reference.displayLabel && (
          <div className="text-xs text-muted-foreground mt-1">
            ID: {reference.type}:{reference.id}
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * Enhanced references list component
 */
export function EnrichedReferencesList({
  references,
  isLoading = false,
  error = null,
  onReferenceClick,
  onRefresh,
  className = '',
  compact = false
}: EnrichedReferencesListProps) {
  if (isLoading) {
    return (
      <div className={`flex items-center justify-center py-4 ${className}`}>
        <Loader2 className="h-4 w-4 animate-spin mr-2" />
        <span className="text-sm text-muted-foreground">Loading reference details...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className={`flex items-center gap-3 p-4 rounded-lg border border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-950 ${className}`}>
        <AlertCircle className="h-4 w-4 text-yellow-600 dark:text-yellow-400 flex-shrink-0" />
        <div className="flex-1">
          <p className="text-sm text-yellow-800 dark:text-yellow-200">
            Could not load reference titles
          </p>
          {onRefresh && (
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-xs mt-1"
              onClick={onRefresh}
            >
              <RefreshCw className="h-3 w-3 mr-1" />
              Try again
            </Button>
          )}
        </div>
      </div>
    )
  }

  if (!references || references.length === 0) {
    return null
  }

  if (compact) {
    return (
      <div className={`text-xs text-muted-foreground space-y-1 ${className}`}>
        {references.map((ref) => (
          <div key={`${ref.type}-${ref.id}`} className="flex items-center gap-2">
            <span className="font-medium text-foreground">[{ref.number}]</span>
            <span>{ref.displayLabel}</span>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className={`space-y-2 ${className}`}>
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-foreground">
          References ({references.length})
        </h4>
        {onRefresh && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-xs"
            onClick={onRefresh}
          >
            <RefreshCw className="h-3 w-3 mr-1" />
            Refresh
          </Button>
        )}
      </div>

      <div className="space-y-1">
        {references.map((reference) => (
          <ReferenceItem
            key={`${reference.type}-${reference.id}`}
            reference={reference}
            onClick={() => onReferenceClick?.(reference.type, reference.id)}
          />
        ))}
      </div>
    </div>
  )
}