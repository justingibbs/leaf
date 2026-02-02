import { create } from 'zustand'
import type { WsEvent, FileEvent, Execution } from '@/api/types'

interface EventStoreState {
  events: FileEvent[]
  recentExecutions: Execution[]
  addEvent: (event: FileEvent) => void
  updateEvent: (eventId: string, updates: Partial<FileEvent>) => void
  addExecution: (execution: Execution) => void
  updateExecution: (executionId: string, updates: Partial<Execution>) => void
  clearEvents: () => void
}

const MAX_EVENTS = 100

export const useEventStore = create<EventStoreState>((set) => ({
  events: [],
  recentExecutions: [],

  addEvent: (event) =>
    set((state) => ({
      events: [event, ...state.events].slice(0, MAX_EVENTS),
    })),

  updateEvent: (eventId, updates) =>
    set((state) => ({
      events: state.events.map((e) =>
        e.id === eventId ? { ...e, ...updates } : e
      ),
    })),

  addExecution: (execution) =>
    set((state) => ({
      recentExecutions: [execution, ...state.recentExecutions].slice(0, MAX_EVENTS),
    })),

  updateExecution: (executionId, updates) =>
    set((state) => ({
      recentExecutions: state.recentExecutions.map((e) =>
        e.id === executionId ? { ...e, ...updates } : e
      ),
    })),

  clearEvents: () => set({ events: [], recentExecutions: [] }),
}))

// Helper to process WebSocket events
export function processWsEvent(event: WsEvent) {
  const store = useEventStore.getState()

  if (event.type === 'file.created' || event.type === 'file.modified') {
    const fileEvent: FileEvent = {
      id: event.data.event_id,
      type: event.type,
      timestamp: event.data.timestamp,
      payload: event.data.payload,
      status: event.data.status as FileEvent['status'],
    }
    store.addEvent(fileEvent)
  } else if (event.type === 'execution.started') {
    const execution: Execution = {
      id: event.data.execution_id,
      card_id: event.data.card_id,
      event_id: event.data.event_id,
      status: 'running',
      started_at: new Date().toISOString(),
    }
    store.addExecution(execution)
  } else if (event.type === 'execution.completed') {
    store.updateExecution(event.data.execution_id, {
      status: 'completed',
      completed_at: new Date().toISOString(),
    })
  } else if (event.type === 'execution.failed') {
    store.updateExecution(event.data.execution_id, {
      status: 'failed',
      error: event.data.error,
    })
  }
}
