/**
 * Advanced Batch Upload Dialog with comprehensive progress tracking,
 * error handling, and user experience features.
 */

'use client'

import React, { useState, useEffect, useCallback, useRef } from 'react'
import { useDropzone } from 'react-dropzone'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

import { Upload, File, X, Pause, Play, Square, AlertCircle, CheckCircle, Clock, Zap, HardDrive, Wifi } from 'lucide-react'

import { useBatchUpload } from '@/lib/hooks/use-batch-upload'
import { useNotebooks } from '@/lib/hooks/use-notebooks'
import { useSettings } from '@/lib/hooks/use-settings'
import { cn } from '@/lib/utils'
import { formatFileSize, formatTimeRemaining } from '@/lib/utils/format'
import { NotebookResponse } from '@/lib/types/api'

interface BatchUploadDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  initialNotebookIds?: string[]
  notebookId?: string
  onSuccess?: () => void
}

interface FileItem {
  file: File
  id: string
  status: 'pending' | 'uploading' | 'validating' | 'processing' | 'completed' | 'failed' | 'retrying'
  progress: number
  error?: string
  retryCount: number
  uploadSpeed?: number
  estimatedTimeRemaining?: number
}

const BATCH_STATUS_CONFIG = {
  pending: { icon: Clock, color: 'text-gray-500', label: 'Pending' },
  uploading: { icon: Upload, color: 'text-blue-500', label: 'Uploading' },
  validating: { icon: AlertCircle, color: 'text-yellow-500', label: 'Validating' },
  processing: { icon: Zap, color: 'text-purple-500', label: 'Processing' },
  completed: { icon: CheckCircle, color: 'text-green-500', label: 'Completed' },
  failed: { icon: X, color: 'text-red-500', label: 'Failed' },
  retrying: { icon: Clock, color: 'text-orange-500', label: 'Retrying' },
}

const PRIORITY_CONFIG = {
  low: { label: 'Low', color: 'bg-gray-100 text-gray-800', icon: Clock },
  normal: { label: 'Normal', color: 'bg-blue-100 text-blue-800', icon: HardDrive },
  high: { label: 'High', color: 'bg-purple-100 text-purple-800', icon: Zap },
  urgent: { label: 'Urgent', color: 'bg-red-100 text-red-800', icon: Wifi },
}

export function BatchUploadDialog({
  open,
  onOpenChange,
  initialNotebookIds = [],
  notebookId,
  onSuccess,
}: BatchUploadDialogProps) {
  const [files, setFiles] = useState<FileItem[]>([])
  const [selectedNotebooks, setSelectedNotebooks] = useState<string[]>(initialNotebookIds)
  const [priority, setPriority] = useState<'low' | 'normal' | 'high' | 'urgent'>('normal')
  const [autoStart, setAutoStart] = useState(true)
  const [activeTab, setActiveTab] = useState<'upload' | 'progress'>('upload')
  const [dragActive, setDragActive] = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null)

  const notebooksQuery = useNotebooks()
  const { data: settings } = useSettings()
  const batchUpload = useBatchUpload()
  const [embedEnabled, setEmbedEnabled] = useState<boolean | null>(null)

  // Sync notebook selection when parent dialog opens or defaults change
  useEffect(() => {
    if (!open) {
      return
    }

    const fallback: string[] = Array.isArray(initialNotebookIds)
      ? initialNotebookIds
      : []
    const next = notebookId ? [notebookId] : fallback
    setSelectedNotebooks((prev) => {
      const prevKey = prev.join(',')
      const nextKey = next.join(',')
      return prevKey === nextKey ? prev : next
    })
  }, [open, notebookId, initialNotebookIds])

  // Calculate batch statistics
  const totalSize = files.reduce((sum, file) => sum + file.file.size, 0)
  const completedFiles = files.filter(f => f.status === 'completed').length
  const failedFiles = files.filter(f => f.status === 'failed').length

  // Auto-switch to progress tab when uploading starts
  useEffect(() => {
    if (batchUpload.currentBatch && batchUpload.currentBatch.status !== 'initializing') {
      setActiveTab('progress')
    }
  }, [batchUpload.currentBatch])

  // Update file statuses from batch upload hook
  useEffect(() => {
    if (batchUpload.currentBatch?.files) {
      setFiles(prevFiles =>
        prevFiles.map(fileItem => {
          const batchFile = batchUpload.currentBatch!.files.find(
            bf => bf.original_filename === fileItem.file.name
          )

          if (batchFile) {
            return {
              ...fileItem,
              status: batchFile.status as FileItem['status'],
              progress: Math.max(batchFile.upload_progress, batchFile.processing_progress),
              error: batchFile.error_message,
              retryCount: batchFile.retry_count,
            }
          }

          return fileItem
        })
      )
    }
  }, [batchUpload.currentBatch])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: useCallback((acceptedFiles: File[]) => {
      const newFiles: FileItem[] = acceptedFiles.map(file => ({
        file,
        id: `${file.name}-${file.size}-${Date.now()}`,
        status: 'pending' as const,
        progress: 0,
        retryCount: 0,
      }))

      setFiles(prev => [...prev, ...newFiles])
    }, []),
    onDragEnter: useCallback(() => setDragActive(true), []),
    onDragLeave: useCallback(() => setDragActive(false), []),
    multiple: true,
    noClick: true,
  })

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(event.target.files || [])
    const newFiles: FileItem[] = selectedFiles.map(file => ({
      file,
      id: `${file.name}-${file.size}-${Date.now()}`,
      status: 'pending' as const,
      progress: 0,
      retryCount: 0,
    }))

    setFiles(prev => [...prev, ...newFiles])
  }

  const removeFile = (fileId: string) => {
    setFiles(prev => prev.filter(f => f.id !== fileId))
  }

  const clearCompletedFiles = () => {
    setFiles(prev => prev.filter(f => f.status !== 'completed'))
  }

  const retryFailedFiles = () => {
    // This would trigger retry logic via the batch upload hook
    setFiles(prev => prev.map(f =>
      f.status === 'failed' ? { ...f, status: 'retrying', progress: 0 } : f
    ))
  }

  const handleStartUpload = async () => {
    if (files.length === 0) return

    const uploadFiles = files.map(f => f.file)

    try {
      await batchUpload.startBatchUpload({
        files: uploadFiles,
        notebookIds: selectedNotebooks,
        priority,
        autoStart,
        embed: embedEnabled === null ? undefined : embedEnabled,
      })
      onSuccess?.()
    } catch (error) {
      console.error('Failed to start batch upload:', error)
    }
  }

  const handlePauseUpload = async () => {
    if (batchUpload.currentBatch?.batch_id) {
      await batchUpload.pauseBatch(batchUpload.currentBatch.batch_id)
    }
  }

  const handleResumeUpload = async () => {
    if (batchUpload.currentBatch?.batch_id) {
      await batchUpload.resumeBatch(batchUpload.currentBatch.batch_id)
    }
  }

  const handleCancelUpload = async () => {
    if (batchUpload.currentBatch?.batch_id) {
      await batchUpload.cancelBatch(batchUpload.currentBatch.batch_id)
    }
  }

  const resetUpload = () => {
    setFiles([])
    setActiveTab('upload')
    batchUpload.reset()
    setEmbedEnabled(null)
  }

  const handleClose = () => {
    let shouldClose = true
    if (batchUpload.currentBatch?.status &&
        !['completed', 'failed', 'cancelled'].includes(batchUpload.currentBatch.status)) {
      // Ask for confirmation if upload is in progress
      if (confirm('Upload is still in progress. Are you sure you want to close?')) {
        handleCancelUpload()
      } else {
        shouldClose = false
      }
    }
    if (shouldClose) {
      onOpenChange(false)
      setEmbedEnabled(null)
    }
  }

  const StatusIcon = BATCH_STATUS_CONFIG[files[0]?.status || 'pending'].icon

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5" />
            Batch Upload Files
          </DialogTitle>
          <DialogDescription>
            Upload multiple files at once with progress tracking and intelligent processing.
          </DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as 'upload' | 'progress')} className="flex-1 flex flex-col">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="upload" className="flex items-center gap-2">
              <File className="h-4 w-4" />
              Select Files ({files.length})
            </TabsTrigger>
            <TabsTrigger value="progress" className="flex items-center gap-2">
              <StatusIcon className="h-4 w-4" />
              Progress & Status
            </TabsTrigger>
          </TabsList>

          <TabsContent value="upload" className="flex-1 overflow-hidden flex flex-col mt-4">
            <div className="space-y-4 flex-1 overflow-hidden flex flex-col">
              {/* File Selection Area */}
              <div
                {...getRootProps()}
                className={cn(
                  "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors",
                  isDragActive || dragActive
                    ? "border-primary bg-primary/5"
                    : "border-gray-300 hover:border-gray-400",
                  "flex-1 flex flex-col items-center justify-center min-h-[200px]"
                )}
              >
                <input {...getInputProps()} />
                <Upload className="h-12 w-12 text-gray-400 mb-4" />

                <div className="space-y-2">
                  <p className="text-lg font-medium">
                    {isDragActive ? "Drop files here" : "Drag & drop files here"}
                  </p>
                  <p className="text-sm text-gray-500">
                    or click to select files
                  </p>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={(e) => {
                      e.stopPropagation()
                      fileInputRef.current?.click()
                    }}
                  >
                    Browse Files
                  </Button>
                </div>

                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  onChange={handleFileSelect}
                  className="hidden"
                />
              </div>

              {/* Configuration */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Assign to Notebooks</Label>
                  <Select
                    value={selectedNotebooks.join(',')}
                    onValueChange={(value) => setSelectedNotebooks(value.split(',').filter(Boolean))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select notebooks (optional)" />
                    </SelectTrigger>
                    <SelectContent>
                      {notebooksQuery.data?.map((notebook: NotebookResponse) => (
                        <SelectItem key={notebook.id} value={notebook.id}>
                          {notebook.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Processing Priority</Label>
                  <Select value={priority} onValueChange={(value: 'low' | 'normal' | 'high' | 'urgent') => setPriority(value)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(PRIORITY_CONFIG).map(([key, config]) => {
                        const Icon = config.icon
                        return (
                          <SelectItem key={key} value={key}>
                            <div className="flex items-center gap-2">
                              <Icon className="h-4 w-4" />
                              {config.label}
                            </div>
                          </SelectItem>
                        )
                      })}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Embedding</Label>
                  <label className="flex items-start gap-3 p-3 border border-border rounded-md hover:bg-muted cursor-pointer">
                    <Checkbox
                      checked={embedEnabled ?? false}
                      onCheckedChange={(checked) => setEmbedEnabled(checked === true)}
                      className="mt-0.5"
                    />
                    <div className="flex-1">
                      <span className="text-sm font-medium block">Embed content for vector search</span>
                      <p className="text-xs text-muted-foreground mt-1">
                        Enables semantic search and notebook Q&amp;A for uploaded files.
                      </p>
                      {settings?.default_embedding_option && (
                        <p className="text-xs text-muted-foreground mt-2">
                          Workspace default: <span className="font-medium capitalize">{settings.default_embedding_option}</span>. Toggle to override for this batch.
                        </p>
                      )}
                    </div>
                  </label>
                </div>
              </div>

              {/* Files List */}
              {files.length > 0 && (
                <div className="flex-1 overflow-hidden flex flex-col">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-medium">Selected Files ({files.length})</h3>
                    <div className="flex items-center gap-2 text-sm text-gray-500">
                      <span>Total: {formatFileSize(totalSize)}</span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={clearCompletedFiles}
                        disabled={!files.some(f => f.status === 'completed')}
                      >
                        Clear Completed
                      </Button>
                    </div>
                  </div>

                  <ScrollArea className="flex-1 border rounded-md">
                    <div className="p-2 space-y-2">
                      {files.map((fileItem) => {
                        const StatusConfig = BATCH_STATUS_CONFIG[fileItem.status]
                        const StatusIcon = StatusConfig.icon

                        return (
                          <Card key={fileItem.id} className="p-3">
                            <CardContent className="p-0">
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3 flex-1 min-w-0">
                                  <StatusIcon className={cn("h-5 w-5", StatusConfig.color)} />

                                  <div className="flex-1 min-w-0">
                                    <p className="font-medium truncate">{fileItem.file.name}</p>
                                    <div className="flex items-center gap-2 text-sm text-gray-500">
                                      <span>{formatFileSize(fileItem.file.size)}</span>
                                      {fileItem.retryCount > 0 && (
                                        <Badge variant="outline" className="text-xs">
                                          Retry {fileItem.retryCount}
                                        </Badge>
                                      )}
                                      {fileItem.error && (
                                        <TooltipProvider>
                                          <Tooltip>
                                            <TooltipTrigger>
                                              <AlertCircle className="h-3 w-3 text-red-500" />
                                            </TooltipTrigger>
                                            <TooltipContent>
                                              <p className="max-w-xs text-sm">{fileItem.error}</p>
                                            </TooltipContent>
                                          </Tooltip>
                                        </TooltipProvider>
                                      )}
                                    </div>
                                  </div>
                                </div>

                                <div className="flex items-center gap-2">
                                  <Badge variant="outline" className={StatusConfig.color}>
                                    {StatusConfig.label}
                                  </Badge>

                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => removeFile(fileItem.id)}
                                    disabled={fileItem.status === 'uploading' || fileItem.status === 'processing'}
                                  >
                                    <X className="h-4 w-4" />
                                  </Button>
                                </div>
                              </div>

                              {fileItem.progress > 0 && (
                                <div className="mt-2">
                                  <Progress value={fileItem.progress} className="h-2" />
                                </div>
                              )}
                            </CardContent>
                          </Card>
                        )
                      })}
                    </div>
                  </ScrollArea>
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="progress" className="flex-1 overflow-hidden flex flex-col mt-4">
            {batchUpload.currentBatch ? (
              <div className="space-y-4 flex-1 overflow-hidden flex flex-col">
                {/* Overall Progress */}
                <Card>
                  <CardContent className="p-6">
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <h3 className="font-medium">Overall Progress</h3>
                        <Badge variant="outline">
                          Normal Priority
                        </Badge>
                      </div>

                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span>{batchUpload.currentBatch.processed_files} / {batchUpload.currentBatch.total_files} files</span>
                          <span>{batchUpload.currentBatch.progress_percentage.toFixed(1)}%</span>
                        </div>
                        <Progress value={batchUpload.currentBatch.progress_percentage} className="h-3" />
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                          <span className="text-gray-500">Completed:</span>
                          <div className="font-medium text-green-600">{batchUpload.currentBatch.processed_files}</div>
                        </div>
                        <div>
                          <span className="text-gray-500">Failed:</span>
                          <div className="font-medium text-red-600">{batchUpload.currentBatch.failed_files}</div>
                        </div>
                        <div>
                          <span className="text-gray-500">Size:</span>
                          <div className="font-medium">{formatFileSize(batchUpload.currentBatch.total_size)}</div>
                        </div>
                        <div>
                          <span className="text-gray-500">Time:</span>
                          <div className="font-medium">
                            {batchUpload.currentBatch.estimated_time_remaining
                              ? formatTimeRemaining(batchUpload.currentBatch.estimated_time_remaining)
                              : '--'}
                          </div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Control Buttons */}
                <div className="flex items-center gap-2">
                  {batchUpload.currentBatch.status === 'paused' && (
                    <Button onClick={handleResumeUpload} variant="default">
                      <Play className="h-4 w-4 mr-2" />
                      Resume
                    </Button>
                  )}

                  {['uploading', 'validating', 'processing'].includes(batchUpload.currentBatch.status) && (
                    <Button onClick={handlePauseUpload} variant="outline">
                      <Pause className="h-4 w-4 mr-2" />
                      Pause
                    </Button>
                  )}

                  <Button
                    onClick={handleCancelUpload}
                    variant="outline"
                    disabled={['completed', 'failed', 'cancelled'].includes(batchUpload.currentBatch.status)}
                  >
                    <Square className="h-4 w-4 mr-2" />
                    Cancel
                  </Button>

                  {failedFiles > 0 && (
                    <Button onClick={retryFailedFiles} variant="outline">
                      <AlertCircle className="h-4 w-4 mr-2" />
                      Retry Failed ({failedFiles})
                    </Button>
                  )}

                  <div className="flex-1" />

                  <Badge
                    variant="outline"
                    className={cn(
                      BATCH_STATUS_CONFIG[batchUpload.currentBatch.status as keyof typeof BATCH_STATUS_CONFIG]?.color
                    )}
                  >
                    {BATCH_STATUS_CONFIG[batchUpload.currentBatch.status as keyof typeof BATCH_STATUS_CONFIG]?.label}
                  </Badge>
                </div>

                {/* Individual File Progress */}
                <div className="flex-1 overflow-hidden flex flex-col">
                  <h3 className="font-medium mb-2">File Details</h3>
                  <ScrollArea className="flex-1 border rounded-md">
                    <div className="p-2 space-y-2">
                      {batchUpload.currentBatch.files.map((file, index) => {
                        const StatusConfig = BATCH_STATUS_CONFIG[file.status as keyof typeof BATCH_STATUS_CONFIG]
                        const StatusIcon = StatusConfig.icon

                        return (
                          <Card key={index} className="p-3">
                            <CardContent className="p-0">
                              <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-3 flex-1 min-w-0">
                                  <StatusIcon className={cn("h-4 w-4", StatusConfig.color)} />
                                  <span className="font-medium truncate">{file.original_filename}</span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <span className="text-sm text-gray-500">
                                    {formatFileSize(file.file_size)}
                                  </span>
                                  <Badge variant="outline" className={StatusConfig.color}>
                                    {StatusConfig.label}
                                  </Badge>
                                </div>
                              </div>

                              <div className="space-y-1">
                                <div className="flex justify-between text-xs text-gray-500">
                                  <span>Upload: {file.upload_progress.toFixed(1)}%</span>
                                  <span>Processing: {file.processing_progress.toFixed(1)}%</span>
                                </div>
                                <Progress
                                  value={Math.max(file.upload_progress, file.processing_progress)}
                                  className="h-1"
                                />
                                {file.error_message && (
                                  <p className="text-xs text-red-600 mt-1">{file.error_message}</p>
                                )}
                              </div>
                            </CardContent>
                          </Card>
                        )
                      })}
                    </div>
                  </ScrollArea>
                </div>
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center text-gray-500">
                <div className="text-center">
                  <Upload className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No upload in progress</p>
                  <Button
                    variant="outline"
                    className="mt-4"
                    onClick={() => setActiveTab('upload')}
                  >
                    Go to Upload Tab
                  </Button>
                </div>
              </div>
            )}
          </TabsContent>
        </Tabs>

        <DialogFooter className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="auto-start"
                checked={autoStart}
                onCheckedChange={(checked) => setAutoStart(checked as boolean)}
              />
              <Label htmlFor="auto-start" className="text-sm">Auto-start upload</Label>
            </div>

            {files.length > 0 && (
              <span className="text-sm text-gray-500">
                {files.length} files • {formatFileSize(totalSize)}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {batchUpload.currentBatch?.status === 'completed' && (
              <Button variant="outline" onClick={resetUpload}>
                New Upload
              </Button>
            )}

            <Button
              onClick={handleStartUpload}
              disabled={files.length === 0 || batchUpload.currentBatch?.status === 'uploading'}
            >
              {batchUpload.currentBatch?.status === 'uploading' ? 'Uploading...' : 'Start Upload'}
            </Button>

            <Button variant="outline" onClick={handleClose}>
              Close
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
  useEffect(() => {
    if (!open) {
      return
    }
    if (!settings) {
      setEmbedEnabled((prev) => (prev === null ? false : prev))
      return
    }
    setEmbedEnabled((prev) => {
      if (prev !== null) {
        return prev
      }
      const option = settings.default_embedding_option
      if (!option) {
        return false
      }
      return option === 'always' || option === 'ask'
    })
  }, [open, settings])

  useEffect(() => {
    if (!open) {
      setEmbedEnabled(null)
    }
  }, [open])
