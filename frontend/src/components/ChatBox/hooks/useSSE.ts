// src/components/ChatBox/hooks/useSSE.ts
// SSE 流式处理 Hook
//
// 功能说明：
// 1. 处理 Server-Sent Events 流式响应
// 2. 支持 POST 请求（带 Authorization header）
// 3. 支持中断请求

import { useState, useCallback, useRef } from 'react';
import { getAccessToken, chatApi, SSEEvent } from '@/lib/api';

interface UseSSEOptions {
  onToken: (token: string) => void;
  onDone: (data: { sessionId: string; messageId: string }) => void;
  onError: (error: string) => void;
}

interface UseSSEReturn {
  sendMessage: (sessionId: string | null, message: string) => Promise<string | null>;
  isStreaming: boolean;
  abort: () => void;
}

export function useSSE({ onToken, onDone, onError }: UseSSEOptions): UseSSEReturn {
  const [isStreaming, setIsStreaming] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const abort = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsStreaming(false);
    }
  }, []);

  const sendMessage = useCallback(
    async (sessionId: string | null, message: string): Promise<string | null> => {
      // 如果正在流式传输，先中断
      if (isStreaming) {
        abort();
      }

      setIsStreaming(true);
      abortControllerRef.current = new AbortController();

      try {
        const token = getAccessToken();
        if (!token) {
          throw new Error('未登录');
        }

        const response = await fetch(chatApi.getStreamUrl(), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            session_id: sessionId,
            message,
          }),
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `请求失败: ${response.status}`);
        }

        if (!response.body) {
          throw new Error('响应体为空');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let resultSessionId: string | null = null;

        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            break;
          }

          // 解码并添加到缓冲区
          buffer += decoder.decode(value, { stream: true });

          // 按行处理 SSE 数据
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // 保留最后不完整的行

          for (const line of lines) {
            // SSE 格式: "event: message\ndata: {...}"
            if (line.startsWith('data: ')) {
              const jsonStr = line.slice(6).trim();
              if (!jsonStr) continue;

              try {
                const event = JSON.parse(jsonStr) as SSEEvent;

                switch (event.type) {
                  case 'token':
                    onToken(event.content);
                    break;
                  case 'done':
                    resultSessionId = event.session_id;
                    onDone({
                      sessionId: event.session_id,
                      messageId: event.message_id,
                    });
                    break;
                  case 'error':
                    onError(event.error);
                    break;
                }
              } catch (parseError) {
                console.error('解析 SSE 数据失败:', parseError, jsonStr);
              }
            }
          }
        }

        return resultSessionId;
      } catch (error) {
        if (error instanceof Error && error.name === 'AbortError') {
          // 用户主动中断，不报错
          return null;
        }
        const errorMessage = error instanceof Error ? error.message : '发送失败';
        onError(errorMessage);
        return null;
      } finally {
        setIsStreaming(false);
        abortControllerRef.current = null;
      }
    },
    [isStreaming, abort, onToken, onDone, onError]
  );

  return {
    sendMessage,
    isStreaming,
    abort,
  };
}

export default useSSE;
