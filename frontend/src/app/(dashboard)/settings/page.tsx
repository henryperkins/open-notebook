'use client'

import { useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { toast } from 'sonner'
import { AppShell } from '@/components/layout/AppShell'
import { SettingsForm } from './components/SettingsForm'
import { useSettings } from '@/lib/hooks/use-settings'
import { Button } from '@/components/ui/button'
import { RefreshCw } from 'lucide-react'

export default function SettingsPage() {
  const { refetch } = useSettings()
  const router = useRouter()
  const searchParams = useSearchParams()

  useEffect(() => {
    if (!searchParams) return

    const success = searchParams.get('success')
    const integration = searchParams.get('integration')

    if (success === 'true' && integration === 'google') {
      toast.success('Google Drive connected successfully.')
      // Clean up the URL so we don't show the toast again on refresh.
      router.replace('/settings', { scroll: false })
    }
  }, [searchParams, router])

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto">
        <div className="p-6">
          <div className="max-w-4xl">
            <div className="flex items-center gap-4 mb-6">
              <h1 className="text-2xl font-bold">Settings</h1>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
            <SettingsForm />
          </div>
        </div>
      </div>
    </AppShell>
  )
}
