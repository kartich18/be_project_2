import { useEffect, useRef, useCallback } from 'react';

type SSEHandler = (data: unknown) => void;
type EventMap = Record<string, SSEHandler>;

/**
 * Wraps the browser EventSource API for SSE streams that require a JWT token.
 * Since EventSource cannot send custom headers, the token is passed as a query param.
 */
export function useSSE(path: string, handlers: EventMap, enabled = true) {
  const esRef = useRef<EventSource | null>(null);
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  const connect = useCallback(() => {
    const token = localStorage.getItem('access_token');
    if (!token || !enabled) return;

    const url = `${path}?token=${encodeURIComponent(token)}`;
    const es = new EventSource(url);
    esRef.current = es;

    // Bind all registered event types
    Object.entries(handlersRef.current).forEach(([event, handler]) => {
      es.addEventListener(event, (e: MessageEvent) => {
        try {
          handler(JSON.parse(e.data));
        } catch {
          handler(e.data);
        }
      });
    });

    es.onerror = () => {
      es.close();
      esRef.current = null;
      // Reconnect after 5 s
      setTimeout(connect, 5000);
    };
  }, [path, enabled]);

  useEffect(() => {
    if (enabled) connect();
    return () => {
      esRef.current?.close();
      esRef.current = null;
    };
  }, [connect, enabled]);
}
