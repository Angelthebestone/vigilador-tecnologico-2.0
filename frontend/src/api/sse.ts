import type { SSEConnectionStatus } from '@/types';

export class SseClient {
  private eventSource: EventSource | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private readonly maxReconnectDelay = 30_000;
  private _connectionStatus: SSEConnectionStatus = 'disconnected';
  private onStatusChangeCallback: ((status: SSEConnectionStatus) => void) | null = null;

  private handlers: Record<string, (data: unknown) => void>;

  constructor(
    sessionId: string,
    handlers: Record<string, (data: unknown) => void>,
    baseUrl: string = import.meta.env.VITE_API_BASE_URL ??
      'http://localhost:8000/api/v2',
  ) {
    this.handlers = handlers;
    this.url = `${baseUrl}/research/${sessionId}/stream`;
  }

  connect(): void {
    if (this.eventSource) this.disconnect();

    this.eventSource = new EventSource(this.url);

    this.eventSource.onmessage = () => {};

    for (const [eventType, handler] of Object.entries(this.handlers)) {
      this.eventSource.addEventListener(eventType, (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data) as unknown;
          handler(data);
        } catch {
          // skip malformed JSON
        }
      });
    }

    this.eventSource.onopen = () => {
      this.reconnectAttempts = 0;
      this._connectionStatus = 'connected';
      this.onStatusChangeCallback?.('connected');
    };

    this.eventSource.onerror = () => {
      this._connectionStatus = 'connecting';
      this.onStatusChangeCallback?.('connecting');
      this.reconnect();
    };
  }

  disconnect(): void {
    this.eventSource?.close();
    this.eventSource = null;
    this._connectionStatus = 'disconnected';
    this.onStatusChangeCallback?.('disconnected');
  }

  onStatusChange(callback: (status: SSEConnectionStatus) => void): void {
    this.onStatusChangeCallback = callback;
  }

  private reconnect(): void {
    this.reconnectAttempts++;
    const delay = Math.min(
      1000 * 2 ** this.reconnectAttempts,
      this.maxReconnectDelay,
    );
    setTimeout(() => this.connect(), delay);
  }

  get connectionStatus(): SSEConnectionStatus {
    return this._connectionStatus;
  }
}
