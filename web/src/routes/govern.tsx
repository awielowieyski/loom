/* eslint-disable react-refresh/only-export-components */
import { useState, useCallback } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { HealthDashboard } from '@/components/govern/HealthDashboard'
import { EvalTrends } from '@/components/govern/EvalTrends'
import { UsageHeatmap } from '@/components/govern/UsageHeatmap'
import { ReviewQueue } from '@/components/govern/ReviewQueue'
import { ReviewInterface } from '@/components/govern/ReviewInterface'
import type { GovernanceQueueItem, GovernanceStage } from '@/types/api'

export const Route = createFileRoute('/govern')({
  component: GovernView,
})

function GovernView() {
  const [selectedItem, setSelectedItem] = useState<GovernanceQueueItem | null>(null)
  const [selectedStage, setSelectedStage] = useState<GovernanceStage>('quarantine')

  const handleSelect = useCallback((item: GovernanceQueueItem) => {
    setSelectedItem(item)
  }, [])

  const handleReviewComplete = useCallback(() => {
    setSelectedItem(null)
  }, [])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Govern</h1>
        <p className="text-muted-foreground">
          Operate the registry pipeline: intake, canonicalization, deduplication, evaluation, and publication.
        </p>
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="trends">Trends</TabsTrigger>
          <TabsTrigger value="pipeline">Pipeline</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6 pt-4">
          <HealthDashboard />
          <UsageHeatmap />
        </TabsContent>

        <TabsContent value="trends" className="space-y-6 pt-4">
          <EvalTrends />
        </TabsContent>

        <TabsContent value="pipeline" className="pt-4 space-y-4">
          <Tabs value={selectedStage} onValueChange={(value) => setSelectedStage(value as GovernanceStage)}>
            <TabsList>
              <TabsTrigger value="quarantine">Quarantine</TabsTrigger>
              <TabsTrigger value="canonicalization">Canonicalize</TabsTrigger>
              <TabsTrigger value="dedup">Dedup</TabsTrigger>
              <TabsTrigger value="evaluation">Evaluate</TabsTrigger>
              <TabsTrigger value="publication">Publish</TabsTrigger>
            </TabsList>
          </Tabs>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <ReviewQueue
              stage={selectedStage}
              onSelect={handleSelect}
              selectedId={selectedItem?.id}
              className="max-h-[calc(100vh-14rem)] overflow-hidden"
            />
            {selectedItem ? (
              <ReviewInterface
                item={selectedItem}
                onComplete={handleReviewComplete}
                className="max-h-[calc(100vh-14rem)] overflow-hidden"
              />
            ) : (
              <div className="flex items-center justify-center rounded-xl border border-dashed p-12 text-muted-foreground">
                Select an item from the queue to review.
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
