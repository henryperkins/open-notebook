"use client"

import { Control, Controller } from "react-hook-form"
import { FormSection } from "@/components/ui/form-section"
import { CheckboxList } from "@/components/ui/checkbox-list"
import { Checkbox } from "@/components/ui/checkbox"
import { Transformation } from "@/lib/types/transformations"
import { SettingsResponse } from "@/lib/types/api"

interface CreateSourceFormData {
  type: 'link' | 'upload' | 'text'
  title?: string
  url?: string
  content?: string
  file?: FileList | File
  notebooks?: string[]
  transformations?: string[]
  embed: boolean
  async_processing: boolean
}

interface ProcessingStepProps {
  control: Control<CreateSourceFormData>
  transformations: Transformation[]
  selectedTransformations: string[]
  onToggleTransformation: (transformationId: string) => void
  loading?: boolean
  settings?: SettingsResponse
}

export function ProcessingStep({
  control,
  transformations,
  selectedTransformations,
  onToggleTransformation,
  loading = false,
  settings
}: ProcessingStepProps) {
  const transformationItems = transformations.map((transformation) => ({
    id: transformation.id,
    title: transformation.title,
    description: transformation.description
  }))

  return (
    <div className="space-y-8">
      <FormSection
        title="Transformations (optional)"
        description="Apply AI transformations to analyze and extract insights from your content."
      >
        <CheckboxList
          items={transformationItems}
          selectedIds={selectedTransformations}
          onToggle={onToggleTransformation}
          loading={loading}
          emptyMessage="No transformations found."
        />
      </FormSection>

      <FormSection
        title="Processing Settings"
        description="Configure how your source will be processed and stored."
      >
        <div className="space-y-4">
          <Controller
            control={control}
            name="embed"
            render={({ field }) => (
              <label className="flex items-start gap-3 cursor-pointer p-3 rounded-md hover:bg-muted border border-border">
                <Checkbox
                  checked={field.value}
                  onCheckedChange={(checked) => field.onChange(checked === true)}
                  className="mt-0.5"
                />
                <div className="flex-1">
                  <span className="text-sm font-medium block">Enable embedding for search</span>
                  <p className="text-xs text-muted-foreground mt-1">
                    Embedded content powers semantic search, notebook Q&amp;A, and insight generation.
                  </p>
                  {settings?.default_embedding_option && (
                    <p className="text-xs text-muted-foreground mt-2">
                      Default setting: <span className="font-medium capitalize">{settings.default_embedding_option}</span>. Toggle to override for this source.
                    </p>
                  )}
                </div>
              </label>
            )}
          />

          {settings?.default_embedding_option === 'always' && (
            <p className="text-xs text-muted-foreground">
              This workspace embeds content by default. Disable above if you want to skip embedding for this upload.
            </p>
          )}

          {settings?.default_embedding_option === 'never' && (
            <p className="text-xs text-muted-foreground">
              Embedding is disabled by default. Enable above if you want this source to appear in vector search.
            </p>
          )}
        </div>
      </FormSection>
    </div>
  )
}
