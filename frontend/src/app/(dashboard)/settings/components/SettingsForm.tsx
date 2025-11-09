'use client'

import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import { useSettings, useUpdateSettings } from '@/lib/hooks/use-settings'
import { useEffect, useState } from 'react'
import { ChevronDownIcon } from 'lucide-react'
import { getApiUrl } from '@/lib/config'

const settingsSchema = z.object({
  default_content_processing_engine_doc: z.enum(['auto', 'docling', 'simple']).optional(),
  default_content_processing_engine_url: z.enum(['auto', 'firecrawl', 'jina', 'simple']).optional(),
  default_embedding_option: z.enum(['ask', 'always', 'never']).optional(),
  embedding_dimension: z.number().int().min(16).max(32768).optional(),
  auto_delete_files: z.enum(['yes', 'no']).optional(),
})

type SettingsFormData = z.infer<typeof settingsSchema>

export function SettingsForm() {
  const { data: settings, isLoading, error } = useSettings()
  const updateSettings = useUpdateSettings()
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({})
  const [hasResetForm, setHasResetForm] = useState(false)

  // OAuth (Google Drive) local state
  const [gdriveConnected, setGdriveConnected] = useState<boolean | null>(null)
  const [gdriveLoading, setGdriveLoading] = useState(false)
  const [gdriveActionLoading, setGdriveActionLoading] = useState(false)
  
  
  const {
    control,
    handleSubmit,
    reset,
    formState: { isDirty }
  } = useForm<SettingsFormData>({
    resolver: zodResolver(settingsSchema),
    defaultValues: {
      default_content_processing_engine_doc: undefined,
      default_content_processing_engine_url: undefined,
      default_embedding_option: undefined,
      embedding_dimension: undefined,
      auto_delete_files: undefined,
    }
  })


  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }))
  }

  useEffect(() => {
    if (!settings || hasResetForm) {
      return
    }

    const formData: SettingsFormData = {
      default_content_processing_engine_doc: settings.default_content_processing_engine_doc as 'auto' | 'docling' | 'simple',
      default_content_processing_engine_url: settings.default_content_processing_engine_url as 'auto' | 'firecrawl' | 'jina' | 'simple',
      default_embedding_option: settings.default_embedding_option as 'ask' | 'always' | 'never',
      embedding_dimension: settings.embedding_dimension ?? undefined,
      auto_delete_files: settings.auto_delete_files as 'yes' | 'no',
    }
    reset(formData)
    setHasResetForm(true)
  }, [hasResetForm, reset, settings])

  // Fetch Google Drive integration status
  useEffect(() => {
    let cancelled = false
    const run = async () => {
      try {
        setGdriveLoading(true)
        const apiUrl = await getApiUrl()
        const res = await fetch(`${apiUrl}/api/oauth/providers/google_drive/info`, {
          credentials: 'include',
        })
        if (!res.ok) return
        const data = await res.json()
        if (!cancelled) {
          setGdriveConnected(Boolean(data?.is_connected))
        }
      } catch {
        // ignore network errors for status
      } finally {
        if (!cancelled) setGdriveLoading(false)
      }
    }
    run()
    return () => {
      cancelled = true
    }
  }, [])

  const onSubmit = async (data: SettingsFormData) => {
    await updateSettings.mutateAsync(data)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertTitle>Failed to load settings</AlertTitle>
        <AlertDescription>
          {error instanceof Error ? error.message : 'An unexpected error occurred.'}
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Content Processing</CardTitle>
          <CardDescription>
            Configure how documents and URLs are processed
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-3">
            <Label htmlFor="doc_engine">Document Processing Engine</Label>
            <Controller
              name="default_content_processing_engine_doc"
              control={control}
              render={({ field }) => (
                <Select
                  key={field.value}
                  value={field.value || ''}
                  onValueChange={field.onChange}
                  disabled={field.disabled || isLoading}
                >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select document processing engine" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="auto">Auto (Recommended)</SelectItem>
                      <SelectItem value="docling">Docling</SelectItem>
                      <SelectItem value="simple">Simple</SelectItem>
                    </SelectContent>
                  </Select>
              )}
            />
            <Collapsible open={expandedSections.doc} onOpenChange={() => toggleSection('doc')}>
              <CollapsibleTrigger className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
                <ChevronDownIcon className={`h-4 w-4 transition-transform ${expandedSections.doc ? 'rotate-180' : ''}`} />
                Help me choose
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-2 text-sm text-muted-foreground space-y-2">
                <p>• <strong>Docling</strong> is a little slower but more accurate, specially if the documents contain tables and images.</p>
                <p>• <strong>Simple</strong> will extract any content from the document without formatting it. It&apos;s ok for simple documents, but will lose quality in complex ones.</p>
                <p>• <strong>Auto (recommended)</strong> will try to process through docling and default to simple.</p>
              </CollapsibleContent>
            </Collapsible>
          </div>
          
          <div className="space-y-3">
            <Label htmlFor="url_engine">URL Processing Engine</Label>
            <Controller
              name="default_content_processing_engine_url"
              control={control}
              render={({ field }) => (
                <Select
                  key={field.value}
                  value={field.value || ''}
                  onValueChange={field.onChange}
                  disabled={field.disabled || isLoading}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select URL processing engine" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="auto">Auto (Recommended)</SelectItem>
                    <SelectItem value="firecrawl">Firecrawl</SelectItem>
                    <SelectItem value="jina">Jina</SelectItem>
                    <SelectItem value="simple">Simple</SelectItem>
                  </SelectContent>
                </Select>
              )}
            />
            <Collapsible open={expandedSections.url} onOpenChange={() => toggleSection('url')}>
              <CollapsibleTrigger className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
                <ChevronDownIcon className={`h-4 w-4 transition-transform ${expandedSections.url ? 'rotate-180' : ''}`} />
                Help me choose
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-2 text-sm text-muted-foreground space-y-2">
                <p>• <strong>Firecrawl</strong> is a paid service (with a free tier), and very powerful.</p>
                <p>• <strong>Jina</strong> is a good option as well and also has a free tier.</p>
                <p>• <strong>Simple</strong> will use basic HTTP extraction and will miss content on javascript-based websites.</p>
                <p>• <strong>Auto (recommended)</strong> will try to use firecrawl (if API Key is present). Then, it will use Jina until reaches the limit (or will keep using Jina if you setup the API Key). It will fallback to simple, when none of the previous options is possible.</p>
              </CollapsibleContent>
            </Collapsible>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Embedding and Search</CardTitle>
          <CardDescription>
            Configure search and embedding options
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-3">
            <Label htmlFor="embedding">Default Embedding Option</Label>
            <Controller
              name="default_embedding_option"
              control={control}
              render={({ field }) => (
                <Select
                  key={field.value}
                  value={field.value || ''}
                  onValueChange={field.onChange}
                  disabled={field.disabled || isLoading}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select embedding option" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ask">Ask</SelectItem>
                    <SelectItem value="always">Always</SelectItem>
                    <SelectItem value="never">Never</SelectItem>
                  </SelectContent>
                </Select>
              )}
            />
            <div className="space-y-2">
              <Label htmlFor="embedding_dimension">Embedding Dimension</Label>
              <Controller
                name="embedding_dimension"
                control={control}
                render={({ field }) => (
                  <Input
                    id="embedding_dimension"
                    type="number"
                    min={16}
                    max={32768}
                    value={field.value ?? ''}
                    onChange={(event) => {
                      const value = event.target.value.trim()
                      if (value === '') {
                        field.onChange(undefined)
                        return
                      }
                      const numericValue = Number(value)
                      field.onChange(Number.isNaN(numericValue) ? undefined : numericValue)
                    }}
                    placeholder="e.g. 1024"
                  />
                )}
              />
              <p className="text-xs text-muted-foreground">
                Must match the vector size produced by your embedding model. Changing this will rebuild vector indexes; re-embed existing content to populate the new dimension.
              </p>
            </div>
            <Collapsible open={expandedSections.embedding} onOpenChange={() => toggleSection('embedding')}>
              <CollapsibleTrigger className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
                <ChevronDownIcon className={`h-4 w-4 transition-transform ${expandedSections.embedding ? 'rotate-180' : ''}`} />
                Help me choose
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-2 text-sm text-muted-foreground space-y-2">
                <p>Embedding the content will make it easier to find by you and by your AI agents. If you are running a local embedding model (Ollama, for example), you shouldn&apos;t worry about cost and just embed everything. For online providers, you might want to be careful only if you process a lot of content (like 100s of documents at a day).</p>
                <p>• Choose <strong>always</strong> if you are running a local embedding model or if your content volume is not that big</p>
                <p>• Choose <strong>ask</strong> if you want to decide every time</p>
                <p>• Choose <strong>never</strong> if you don&apos;t care about vector search or do not have an embedding provider.</p>
                <p>As a reference, OpenAI&apos;s text-embedding-3-small costs about 0.02 for 1 million tokens -- which is about 30 times the Wikipedia page for Earth. With Gemini API, Text Embedding 004 is free with a rate limit of 1500 requests per minute.</p>
              </CollapsibleContent>
            </Collapsible>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>File Management</CardTitle>
          <CardDescription>
            Configure file handling and storage options
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-3">
            <Label htmlFor="auto_delete">Auto Delete Files</Label>
            <Controller
              name="auto_delete_files"
              control={control}
              render={({ field }) => (
                <Select
                  key={field.value}
                  value={field.value || ''}
                  onValueChange={field.onChange}
                  disabled={field.disabled || isLoading}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select auto delete option" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="yes">Yes</SelectItem>
                    <SelectItem value="no">No</SelectItem>
                  </SelectContent>
                </Select>
              )}
            />
            <Collapsible open={expandedSections.files} onOpenChange={() => toggleSection('files')}>
              <CollapsibleTrigger className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
                <ChevronDownIcon className={`h-4 w-4 transition-transform ${expandedSections.files ? 'rotate-180' : ''}`} />
                Help me choose
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-2 text-sm text-muted-foreground space-y-2">
                <p>Once your files are uploaded and processed, they are not required anymore. Most users should allow Open Notebook to delete uploaded files from the upload folder automatically. Choose <strong>no</strong>, ONLY if you are using Notebook as the primary storage location for those files (which you shouldn&apos;t be at all). This option will soon be deprecated in favor of always downloading the files.</p>
                <p>• Choose <strong>yes</strong> (recommended) to automatically delete uploaded files after processing</p>
                <p>• Choose <strong>no</strong> only if you need to keep the original files in the upload folder</p>
              </CollapsibleContent>
            </Collapsible>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Integrations</CardTitle>
          <CardDescription>
            Connect to third-party services
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-3">
            <Label>Google Drive</Label>
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm text-muted-foreground">
                Connect your Google Drive account to import files.
              </p>
              <div className="flex items-center gap-3">
                <span className="text-xs text-muted-foreground">
                  {gdriveLoading ? 'Checking...' : gdriveConnected ? 'Connected' : 'Not connected'}
                </span>
                <Button
                  type="button"
                  variant="outline"
                  disabled={gdriveActionLoading || gdriveLoading}
                  onClick={async () => {
                    const apiUrl = await getApiUrl()
                    if (gdriveConnected) {
                      try {
                        setGdriveActionLoading(true)
                        const res = await fetch(`${apiUrl}/api/oauth/integrations/google_drive`, {
                          method: 'DELETE',
                          credentials: 'include',
                        })
                        if (res.ok) {
                          setGdriveConnected(false)
                        }
                      } catch (e) {
                        console.error('Failed to disconnect Google Drive', e)
                      } finally {
                        setGdriveActionLoading(false)
                      }
                    } else {
                      try {
                        setGdriveActionLoading(true)
                        const redirectUrl = `${window.location.origin}/settings?integration=google_drive&success=true`
                        const res = await fetch(`${apiUrl}/api/oauth/authorize`, {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          credentials: 'include',
                          body: JSON.stringify({
                            provider: 'google_drive',
                            redirect_url: redirectUrl,
                          }),
                        })
                        if (!res.ok) {
                          throw new Error(`Failed to initiate OAuth: ${res.status}`)
                        }
                        const data = await res.json()
                        window.location.href = data.authorization_url
                      } catch (e) {
                        console.error('Failed to start OAuth flow', e)
                      } finally {
                        setGdriveActionLoading(false)
                      }
                    }
                  }}
                >
                  {gdriveActionLoading ? 'Please wait...' : gdriveConnected ? 'Disconnect' : 'Connect'}
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button 
          type="submit" 
          disabled={!isDirty || updateSettings.isPending}
        >
          {updateSettings.isPending ? 'Saving...' : 'Save Settings'}
        </Button>
      </div>
    </form>
  )
}
