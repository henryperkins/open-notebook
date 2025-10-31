'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { CheckCircle, Sparkles, Lightbulb, ChevronDown } from 'lucide-react'
import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { convertReferencesToMarkdownLinks, createReferenceLinkComponent } from '@/lib/utils/source-references'
import { getProseStyle } from '@/lib/utils/prose-styles'
import { useStreamingEnrichedReferences } from '@/lib/hooks/use-enriched-references'
import { EnrichedReferencesList } from '@/components/common/EnrichedReferencesList'
import { useModalManager } from '@/lib/hooks/use-modal-manager'
import { toast } from 'sonner'

interface StrategyData {
  reasoning: string
  searches: Array<{ term: string; instructions: string }>
}

interface StreamingResponseProps {
  isStreaming: boolean
  strategy: StrategyData | null
  answers: string[]
  finalAnswer: string | null
}

export function StreamingResponse({
  isStreaming,
  strategy,
  answers,
  finalAnswer
}: StreamingResponseProps) {
  const [strategyOpen, setStrategyOpen] = useState(false)
  const [answersOpen, setAnswersOpen] = useState(false)
  const { openModal } = useModalManager()

  const handleReferenceClick = (type: string, id: string) => {
    const modalType = type === 'source_insight' ? 'insight' : type as 'source' | 'note' | 'insight'

    try {
      openModal(modalType, id)
      // Note: The modal system uses URL parameters and doesn't throw errors for missing items.
      // The modal component itself will handle displaying "not found" states.
      // This try-catch is here for future enhancements or unexpected errors.
    } catch {
      const typeLabel = type === 'source_insight' ? 'insight' : type
      toast.error(`This ${typeLabel} could not be found`)
    }
  }

  if (!strategy && !answers.length && !finalAnswer && !isStreaming) {
    return null
  }

  return (
    <div
      className="space-y-4 mt-6 max-h-[60vh] overflow-y-auto pr-2"
      role="region"
      aria-label="Ask response"
      aria-live="polite"
      aria-busy={isStreaming}
    >
      {/* Strategy Section - Collapsible */}
      {strategy && (
        <Collapsible open={strategyOpen} onOpenChange={setStrategyOpen}>
          <Card>
            <CardHeader>
              <CollapsibleTrigger className="flex items-center justify-between w-full hover:opacity-80">
                <CardTitle className="text-base flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-primary" />
                  Strategy
                </CardTitle>
                <ChevronDown className={`h-4 w-4 transition-transform ${strategyOpen ? 'rotate-180' : ''}`} />
              </CollapsibleTrigger>
            </CardHeader>
            <CollapsibleContent>
              <CardContent className="space-y-3 pt-0">
                <div>
                  <p className="text-sm text-muted-foreground mb-2">Reasoning:</p>
                  <p className="text-sm">{strategy.reasoning}</p>
                </div>
                {strategy.searches.length > 0 && (
                  <div>
                    <p className="text-sm text-muted-foreground mb-2">Search Terms:</p>
                    <div className="space-y-2">
                      {strategy.searches.map((search, i) => (
                        <div key={i} className="flex items-start gap-2">
                          <Badge variant="outline" className="mt-0.5">{i + 1}</Badge>
                          <div className="flex-1">
                            <p className="text-sm font-medium">{search.term}</p>
                            <p className="text-xs text-muted-foreground">{search.instructions}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </CollapsibleContent>
          </Card>
        </Collapsible>
      )}

      {/* Individual Answers Section - Collapsible */}
      {answers.length > 0 && (
        <Collapsible open={answersOpen} onOpenChange={setAnswersOpen}>
          <Card>
            <CardHeader>
              <CollapsibleTrigger className="flex items-center justify-between w-full hover:opacity-80">
                <CardTitle className="text-base flex items-center gap-2">
                  <Lightbulb className="h-4 w-4 text-primary" />
                  Individual Answers ({answers.length})
                </CardTitle>
                <ChevronDown className={`h-4 w-4 transition-transform ${answersOpen ? 'rotate-180' : ''}`} />
              </CollapsibleTrigger>
            </CardHeader>
            <CollapsibleContent>
              <CardContent className="space-y-2 pt-0">
                {answers.map((answer, i) => (
                  <div key={i} className="p-3 rounded-md bg-muted">
                    <p className="text-sm">{answer}</p>
                  </div>
                ))}
              </CardContent>
            </CollapsibleContent>
          </Card>
        </Collapsible>
      )}

      {/* Final Answer Section - Always Open */}
      {finalAnswer && (
        <Card className="border-primary">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-primary" />
              Final Answer
            </CardTitle>
          </CardHeader>
          <CardContent>
            <FinalAnswerContent
              content={finalAnswer}
              onReferenceClick={handleReferenceClick}
              isStreaming={isStreaming}
            />
          </CardContent>
        </Card>
      )}

      {/* Loading Indicator */}
      {isStreaming && !finalAnswer && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <LoadingSpinner size="sm" />
          <span>Processing your question...</span>
        </div>
      )}
    </div>
  )
}

// Helper component to render final answer with clickable references and enriched titles
function FinalAnswerContent({
  content,
  onReferenceClick,
  isStreaming
}: {
  content: string
  onReferenceClick: (type: string, id: string) => void
  isStreaming: boolean
}) {
  // Use the enriched references hook
  const {
    processedText,
    enrichedData,
    isLoading,
    error,
    LinkComponent,
    refreshMetadata,
    hasReferences
  } = useStreamingEnrichedReferences(content, isStreaming, {
    enableAugmentation: true,
    onReferenceClick,
    showToastOnError: false // Don't show toast for streaming errors
  })

  return (
    <div className="space-y-4">
      {/* Main content */}
      <div className={getProseStyle('streaming')}>
        <ReactMarkdown
          components={{
            a: LinkComponent
          }}
        >
          {processedText}
        </ReactMarkdown>
      </div>

      {/* Enhanced references list */}
      {hasReferences && (
        <div className="border-t pt-4">
          {isStreaming ? (
            <div className="text-sm text-muted-foreground">
              References will appear when streaming completes...
            </div>
          ) : (
            <EnrichedReferencesList
              references={enrichedData || []}
              isLoading={isLoading}
              error={error}
              onReferenceClick={onReferenceClick}
              onRefresh={refreshMetadata}
              compact={false}
            />
          )}
        </div>
      )}
    </div>
  )
}
