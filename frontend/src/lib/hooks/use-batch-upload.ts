/**
 * Comprehensive batch upload hook with progress tracking, error handling,
 * and real-time status updates.
 */

'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useToast } from '@/lib/hooks/use-toast'

import { apiClient } from '@/lib/api/client'
import { useSettings } from '@/lib/hooks/use-settings'

const getErrorDetail = (error: { response?: { data?: { detail?: string } }; message?: string }, fallback: string) => {
  if (error?.response?.data?.detail) {
    return error.response.data.detail
  }
  if (error?.message) {
    return error.message
  }
  return fallback
}

// Types

interface BatchUploadResponse {
  batch_id: string
  status: 'initializing' | 'uploading' | 'validating' | 'processing' | 'completed' | 'failed' | 'cancelled' | 'paused'
  total_files: number
  total_size: number
  estimated_duration?: number
  message: string
}

interface FileProcessingInfo {
  file_id: string
  original_filename: string
  file_size: number
  mime_type: string
  status: 'pending' | 'uploading' | 'uploaded' | 'validating' | 'validated' | 'processing' | 'completed' | 'failed' | 'retrying' | 'skipped'
  error_message?: string
  retry_count: number
  upload_progress: number
  processing_progress: number
  notebook_ids: string[]
}

interface BatchUploadStatusResponse {
  batch_id: string
  status: 'initializing' | 'uploading' | 'validating' | 'processing' | 'completed' | 'failed' | 'cancelled' | 'paused'
  progress_percentage: number
  total_files: number
  processed_files: number
  failed_files: number
  skipped_files: number
  total_size: number
  uploaded_size: number
  files: FileProcessingInfo[]
  estimated_time_remaining?: number
  error_summary: Record<string, number>
  created_at: string
  started_at?: string
  completed_at?: string
}

interface BatchControlResponse {
  success: boolean
  message: string
  batch_id: string
  current_status: string
  progress_percentage: number
}

interface BatchFilesResponse {
  batch_id: string
  total_files: number
  filtered_by_status?: string
  files: {
    file_id: string
    original_filename: string
    file_size: number
    mime_type: string
    status: string
    error_message?: string
    retry_count: number
    upload_progress: number
    processing_progress: number
    notebook_ids: string[]
  }[]
}

interface ActiveBatchesResponse {
  active_batches: {
    batch_id: string
    status: string
    total_files: number
    processed_files: number
    failed_files: number
    progress_percentage: number
    created_at: string
    started_at?: string
    estimated_time_remaining?: number
  }[]
  total_active: number
}

interface BatchStatsResponse {
  user_id: string
  statistics: {
    total_batches: number
    processing_batches: number
    completed_batches: number
    failed_batches: number
    total_files: number
    total_size_bytes: number
    total_size_mb: number
    average_batch_size: number
  }
}

// Query keys
const BATCH_UPLOAD_KEYS = {
  all: ['batch-uploads'] as const,
  active: () => [...BATCH_UPLOAD_KEYS.all, 'active'] as const,
  status: (batchId: string) => [...BATCH_UPLOAD_KEYS.all, 'status', batchId] as const,
  files: (batchId: string, status?: string) => [...BATCH_UPLOAD_KEYS.all, 'files', batchId, status] as const,
  stats: () => [...BATCH_UPLOAD_KEYS.all, 'stats'] as const,
}

// API functions
const batchUploadApi = {
  // Initialize batch upload
  init: async (data: {
    files: File[]
    notebook_ids?: string[]
    priority?: 'low' | 'normal' | 'high' | 'urgent'
    auto_start?: boolean
    embed?: boolean
  }): Promise<BatchUploadResponse> => {
    const formData = new FormData()

    // Add files
    data.files.forEach((file) => {
      formData.append('files', file)
    })

    // Add other fields
    if (data.notebook_ids?.length) {
      formData.append('notebook_ids', data.notebook_ids.join(','))
    }

    if (data.priority) {
      formData.append('priority', data.priority)
    }

    formData.append('auto_start', String(data.auto_start ?? true))
    if (data.embed !== undefined) {
      formData.append('embed', String(data.embed))
    }

    const response = await apiClient.post('/batch-uploads/init', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })

    return response.data
  },

  // Get batch status
  getStatus: async (batchId: string): Promise<BatchUploadStatusResponse> => {
    const response = await apiClient.get(`/batch-uploads/${batchId}/status`)
    return response.data
  },

  // Control batch (pause, resume, cancel)
  control: async (batchId: string, action: 'pause' | 'resume' | 'cancel'): Promise<BatchControlResponse> => {
    const response = await apiClient.post(`/batch-uploads/${batchId}/control`, {
      action,
    })
    return response.data
  },

  // Get batch files
  getFiles: async (batchId: string, statusFilter?: string): Promise<BatchFilesResponse> => {
    const params = statusFilter ? { status_filter: statusFilter } : {}
    const response = await apiClient.get(`/batch-uploads/${batchId}/files`, { params })
    return response.data
  },

  // Get active batches
  getActive: async (): Promise<ActiveBatchesResponse> => {
    const response = await apiClient.get('/batch-uploads/active')
    return response.data
  },

  // Get statistics
  getStats: async (): Promise<BatchStatsResponse> => {
    const response = await apiClient.get('/batch-uploads/stats')
    return response.data
  },

  // Delete batch
  delete: async (batchId: string, force = false): Promise<{ success: boolean; message: string; batch_id: string }> => {
    const response = await apiClient.delete(`/batch-uploads/${batchId}`, {
      params: { force },
    })
    return response.data
  },
}

// Main hook
export function useBatchUpload() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const { data: settings } = useSettings()
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const [currentBatchId, setCurrentBatchId] = useState<string | null>(null)

  // Initialize batch upload mutation
  const initMutation = useMutation({
    mutationFn: batchUploadApi.init,
    onSuccess: (data: BatchUploadResponse) => {
      setCurrentBatchId(data.batch_id)

      // Start polling for status updates
      startStatusPolling(data.batch_id)

      // Invalidate active batches query
      queryClient.invalidateQueries({ queryKey: BATCH_UPLOAD_KEYS.active() })

      toast({
        title: 'Batch Upload Started',
        description: `Started uploading ${data.total_files} files (${(data.total_size / 1024 / 1024).toFixed(1)} MB)`,
      })
    },
    onError: (error: { message?: string; response?: { data?: { detail?: string } } }) => {
      toast({
        title: 'Upload Failed',
        description: getErrorDetail(error, 'Failed to start batch upload'),
        variant: 'destructive',
      })
    },
  })

  // Status polling
  const statusQuery = useQuery({
    queryKey: BATCH_UPLOAD_KEYS.status(currentBatchId || ''),
    queryFn: () => currentBatchId ? batchUploadApi.getStatus(currentBatchId) : null,
    enabled: !!currentBatchId,
    refetchInterval: (data, query) => {
      // Poll more frequently during active processing
      if (!data) return false

      const status = data.status
      if (['uploading', 'validating', 'processing'].includes(status)) {
        return 1000 // Poll every second during active processing
      } else if (['paused', 'initializing'].includes(status)) {
        return 3000 // Poll every 3 seconds for paused/initializing
      } else {
        // Stop polling for completed/failed/cancelled batches
        return false
      }
    },
    staleTime: 0,
  })

  // Control mutations
  const pauseMutation = useMutation({
    mutationFn: (batchId: string) => batchUploadApi.control(batchId, 'pause'),
    onSuccess: (_, batchId) => {
      queryClient.invalidateQueries({ queryKey: BATCH_UPLOAD_KEYS.status(batchId) })
      toast({
        title: 'Upload Paused',
        description: 'Batch upload has been paused',
      })
    },
    onError: (error: { message?: string; response?: { data?: { detail?: string } } }) => {
      toast({
        title: 'Failed to Pause',
        description: getErrorDetail(error, 'Failed to pause upload'),
        variant: 'destructive',
      })
    },
  })

  const resumeMutation = useMutation({
    mutationFn: (batchId: string) => batchUploadApi.control(batchId, 'resume'),
    onSuccess: (_, batchId) => {
      queryClient.invalidateQueries({ queryKey: BATCH_UPLOAD_KEYS.status(batchId) })
      toast({
        title: 'Upload Resumed',
        description: 'Batch upload has been resumed',
      })
    },
    onError: (error: { message?: string; response?: { data?: { detail?: string } } }) => {
      toast({
        title: 'Failed to Resume',
        description: getErrorDetail(error, 'Failed to resume upload'),
        variant: 'destructive',
      })
    },
  })

  const cancelMutation = useMutation({
    mutationFn: (batchId: string) => batchUploadApi.control(batchId, 'cancel'),
    onSuccess: (_, batchId) => {
      queryClient.invalidateQueries({ queryKey: BATCH_UPLOAD_KEYS.active() })
      queryClient.invalidateQueries({ queryKey: BATCH_UPLOAD_KEYS.status(batchId) })
      toast({
        title: 'Upload Cancelled',
        description: 'Batch upload has been cancelled',
      })

      // Stop polling
      stopStatusPolling()
    },
    onError: (error: { message?: string; response?: { data?: { detail?: string } } }) => {
      toast({
        title: 'Failed to Cancel',
        description: getErrorDetail(error, 'Failed to cancel upload'),
        variant: 'destructive',
      })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: ({ batchId, force }: { batchId: string; force?: boolean }) =>
      batchUploadApi.delete(batchId, force),
    onSuccess: (_, { batchId }) => {
      if (batchId === currentBatchId) {
        setCurrentBatchId(null)
        stopStatusPolling()
      }

      // Invalidate queries
      queryClient.invalidateQueries({ queryKey: BATCH_UPLOAD_KEYS.active() })

      toast({
        title: 'Batch Deleted',
        description: 'Batch upload has been deleted',
      })
    },
    onError: (error: { message?: string; response?: { data?: { detail?: string } } }) => {
      toast({
        title: 'Failed to Delete',
        description: getErrorDetail(error, 'Failed to delete batch'),
        variant: 'destructive',
      })
    },
  })

  // Helper functions
  const stopStatusPolling = useCallback(() => {
    setCurrentBatchId(null)

    // Clear any manual polling timeout
    if (pollIntervalRef.current) {
      clearTimeout(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
  }, [])

  const startStatusPolling = useCallback((batchId: string) => {
    // Clear any existing polling
    stopStatusPolling()

    // Set current batch ID
    setCurrentBatchId(batchId)

    // React Query will handle the actual polling via refetchInterval
  }, [stopStatusPolling])

  const startBatchUpload = useCallback(async (data: {
    files: File[]
    notebookIds?: string[]
    priority?: 'low' | 'normal' | 'high' | 'urgent'
    autoStart?: boolean
    embed?: boolean
  }) => {
    const preference = settings?.default_embedding_option
    const embed =
      data.embed !== undefined
        ? data.embed
        : preference === undefined
          ? undefined
          : preference === 'always' || preference === 'ask'

    return initMutation.mutateAsync({
      files: data.files,
      notebook_ids: data.notebookIds,
      priority: data.priority || 'normal',
      auto_start: data.autoStart ?? true,
      embed,
    })
  }, [initMutation, settings])

  const pauseBatch = useCallback(async (batchId: string) => {
    return pauseMutation.mutateAsync(batchId)
  }, [pauseMutation])

  const resumeBatch = useCallback(async (batchId: string) => {
    return resumeMutation.mutateAsync(batchId)
  }, [resumeMutation])

  const cancelBatch = useCallback(async (batchId: string) => {
    return cancelMutation.mutateAsync(batchId)
  }, [cancelMutation])

  const deleteBatch = useCallback(async (batchId: string, force = false) => {
    return deleteMutation.mutateAsync({ batchId, force })
  }, [deleteMutation])

  const reset = useCallback(() => {
    setCurrentBatchId(null)
    stopStatusPolling()
    initMutation.reset()
    pauseMutation.reset()
    resumeMutation.reset()
    cancelMutation.reset()
    deleteMutation.reset()
  }, [initMutation, pauseMutation, resumeMutation, cancelMutation, deleteMutation, stopStatusPolling])

  // Auto-stop polling when batch is completed/failed/cancelled
  useEffect(() => {
    if (statusQuery.data?.status && ['completed', 'failed', 'cancelled'].includes(statusQuery.data.status)) {
      // Keep the data available but reduce polling frequency
      // This allows users to see the final status
    }
  }, [statusQuery.data?.status])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopStatusPolling()
    }
  }, [stopStatusPolling])

  return {
    // Current batch data
    currentBatch: statusQuery.data,
    isLoadingStatus: statusQuery.isLoading,
    statusError: statusQuery.error,

    // Mutations
    startBatchUpload,
    pauseBatch,
    resumeBatch,
    cancelBatch,
    deleteBatch,

    // Mutation states
    isStarting: initMutation.isPending,
    isPausing: pauseMutation.isPending,
    isResuming: resumeMutation.isPending,
    isCancelling: cancelMutation.isPending,
    isDeleting: deleteMutation.isPending,

    // Errors
    startError: initMutation.error,
    pauseError: pauseMutation.error,
    resumeError: resumeMutation.error,
    cancelError: cancelMutation.error,
    deleteError: deleteMutation.error,

    // Utilities
    reset,
    currentBatchId,

    // Auto-refresh control
    refreshStatus: () => statusQuery.refetch(),
  }
}

// Additional hooks for specific batch upload features
export function useActiveBatchUploads() {
  return useQuery({
    queryKey: BATCH_UPLOAD_KEYS.active(),
    queryFn: batchUploadApi.getActive,
    refetchInterval: 5000, // Refresh every 5 seconds
    staleTime: 2000,
  })
}

export function useBatchUploadStats() {
  return useQuery({
    queryKey: BATCH_UPLOAD_KEYS.stats(),
    queryFn: batchUploadApi.getStats,
    refetchInterval: 10000, // Refresh every 10 seconds
    staleTime: 5000,
  })
}

export function useBatchFiles(batchId: string, statusFilter?: string) {
  return useQuery({
    queryKey: BATCH_UPLOAD_KEYS.files(batchId, statusFilter),
    queryFn: () => batchUploadApi.getFiles(batchId, statusFilter),
    enabled: !!batchId,
    refetchInterval: (data, query) => {
      // Only refetch if there are active files
      if (!data?.files) return false

      const hasActiveFiles = data.files.some((file: FileProcessingInfo) =>
        ['uploading', 'validating', 'processing', 'pending', 'retrying'].includes(file.status)
      )

      return hasActiveFiles ? 2000 : false
    },
  })
}
