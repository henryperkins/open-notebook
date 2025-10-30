"use client"

import { Control, FieldErrors, UseFormRegister, useWatch } from "react-hook-form"
import { FileIcon, LinkIcon, FileTextIcon, Upload } from "lucide-react"
import { FormSection } from "@/components/ui/form-section"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Controller } from "react-hook-form"
import { Button } from "@/components/ui/button"

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

const SOURCE_TYPES = [
  {
    value: 'link' as const,
    label: 'Link',
    icon: LinkIcon,
    description: 'Add a web page or URL',
  },
  {
    value: 'upload' as const,
    label: 'Upload',
    icon: FileIcon,
    description: 'Upload a document or file',
  },
  {
    value: 'text' as const,
    label: 'Text',
    icon: FileTextIcon,
    description: 'Add text content directly',
  },
]

interface SourceTypeStepProps {
  control: Control<CreateSourceFormData>
  register: UseFormRegister<CreateSourceFormData>
  errors: FieldErrors<CreateSourceFormData>
  onBatchUpload?: () => void
}

export function SourceTypeStep({ control, register, errors, onBatchUpload }: SourceTypeStepProps) {
  // Watch the selected type to make title conditional
  const selectedType = useWatch({ control, name: 'type' })
  return (
    <div className="space-y-6">
      <FormSection
        title="Source Type"
        description="Choose how you want to add your content"
      >
        <Controller
          control={control}
          name="type"
          render={({ field }) => (
            <Tabs 
              value={field.value || ''} 
              onValueChange={(value) => field.onChange(value as 'link' | 'upload' | 'text')}
              className="w-full"
            >
              <TabsList className="grid w-full grid-cols-3">
                {SOURCE_TYPES.map((type) => {
                  const Icon = type.icon
                  return (
                    <TabsTrigger key={type.value} value={type.value} className="gap-2">
                      <Icon className="h-4 w-4" />
                      {type.label}
                    </TabsTrigger>
                  )
                })}
              </TabsList>
              
              {SOURCE_TYPES.map((type) => (
                <TabsContent key={type.value} value={type.value} className="mt-4">
                  <p className="text-sm text-muted-foreground mb-4">{type.description}</p>
                  
                  {/* Type-specific fields */}
                  {type.value === 'link' && (
                    <div>
                      <Label htmlFor="url" className="mb-2 block">URL *</Label>
                      <Input
                        id="url"
                        {...register('url')}
                        placeholder="https://example.com/article"
                        type="url"
                      />
                      {errors.url && (
                        <p className="text-sm text-destructive mt-1">{errors.url.message}</p>
                      )}
                    </div>
                  )}
                  
                  {type.value === 'upload' && (
                    <div>
                      <Label htmlFor="file" className="mb-2 block">File *</Label>
                      <Input
                        id="file"
                        type="file"
                        {...register('file')}
                        accept=".pdf,.doc,.docx,.txt,.md,.epub,.jpg,.jpeg,.png,.gif,.bmp,.webp,.mp3,.wav,.mp4,.avi,.mov,.csv,.xlsx,.json,.xml,.html"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Supported formats: PDF, DOC, DOCX, TXT, MD, EPUB, Images, Audio, Video, and more
                      </p>

                      {onBatchUpload && (
                        <div className="mt-4">
                          <div className="relative">
                            <div className="absolute inset-0 flex items-center">
                              <span className="w-full border-t" />
                            </div>
                            <div className="relative flex justify-center text-xs uppercase">
                              <span className="bg-background px-2 text-muted-foreground">Or</span>
                            </div>
                          </div>

                          <Button
                            type="button"
                            variant="outline"
                            className="w-full mt-4"
                            onClick={onBatchUpload}
                          >
                            <Upload className="h-4 w-4 mr-2" />
                            Upload Multiple Files
                          </Button>
                          <p className="text-xs text-muted-foreground mt-2">
                            Upload multiple files at once with progress tracking and batch processing
                          </p>
                        </div>
                      )}

                      {errors.file && (
                        <p className="text-sm text-destructive mt-1">{errors.file.message}</p>
                      )}
                    </div>
                  )}
                  
                  {type.value === 'text' && (
                    <div>
                      <Label htmlFor="content" className="mb-2 block">Text Content *</Label>
                      <Textarea
                        id="content"
                        {...register('content')}
                        placeholder="Paste or type your content here..."
                        rows={6}
                      />
                      {errors.content && (
                        <p className="text-sm text-destructive mt-1">{errors.content.message}</p>
                      )}
                    </div>
                  )}
                </TabsContent>
              ))}
            </Tabs>
          )}
        />
        {errors.type && (
          <p className="text-sm text-destructive mt-1">{errors.type.message}</p>
        )}
      </FormSection>

      <FormSection
        title={selectedType === 'text' ? "Title *" : "Title (optional)"}
        description={selectedType === 'text'
          ? "A title is required for text content"
          : "If left empty, a title will be generated from the content"
        }
      >
        <Input
          id="title"
          {...register('title')}
          placeholder="Give your source a descriptive title"
        />
        {errors.title && (
          <p className="text-sm text-destructive mt-1">{errors.title.message}</p>
        )}
      </FormSection>
    </div>
  )
}
