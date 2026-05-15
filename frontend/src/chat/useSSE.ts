import { useEffect, useRef, useCallback } from 'react';
import { createSSEHandlers } from '@/state/sseHandlers';
import { useStore } from '@/state/useStore';
import { API_BASE } from '@/api';
import type { SSEConnectionStatus } from '@/types';

interface SseClientOptions {
  handlers: Record<string, (data: unknown) => void>;
  onStatusChange: (status: SSEConnectionStatus) => void;
}

class SseClient {
  private eventSource: EventSource | null = null;
  private options: SseClientOptions;
  private url: string;

  constructor(url: string, options: SseClientOptions) {
    this.url = url;
    this.options = options;
  }

  connect() {
    if (this.eventSource) return;
    this.options.onStatusChange('connecting');
    this.eventSource = new EventSource(this.url);

    this.eventSource.onopen = () => {
      this.options.onStatusChange('connected');
    };

    for (const [event, handler] of Object.entries(this.options.handlers)) {
      this.eventSource.addEventListener(event, (e: MessageEvent) => {
        try {
          handler(JSON.parse(e.data));
        } catch {
          handler(e.data);
        }
      });
    }

    this.eventSource.onerror = () => {
      this.options.onStatusChange('disconnected');
    };
  }

  disconnect() {
    this.eventSource?.close();
    this.eventSource = null;
    this.options.onStatusChange('disconnected');
  }
}

interface UseSSEOptions {
  sessionId: string | null;
  enabled?: boolean;
}

export function useSSE({ sessionId, enabled = true }: UseSSEOptions) {
  const clientRef = useRef<SseClient | null>(null);
  const setSseStatus = useStore((s) => s.setSseStatus);
  const connectionStatus = useStore((s) => s.sseStatus);

  const createClient = useCallback(() => {
    if (!sessionId) return null;
    const handlers = createSSEHandlers();
    return new SseClient(`${API_BASE}/research/${sessionId}/stream`, {
      handlers,
      onStatusChange: setSseStatus,
    });
  }, [sessionId, setSseStatus]);

  useEffect(() => {
    if (!enabled || !sessionId) return;

    const client = createClient();
    if (!client) return;

    clientRef.current = client;
    client.connect();

    return () => {
      client.disconnect();
      clientRef.current = null;
    };
  }, [sessionId, enabled, createClient]);

  return { connectionStatus };
}
