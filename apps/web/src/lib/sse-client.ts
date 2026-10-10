/**
 * SSE 客户端（基于 fetch + ReadableStream）。
 *
 * 为什么不用 EventSource：后端对话接口是 POST + JSON body，
 * 而原生 EventSource 只支持 GET，没法带请求体，所以只能自己解析流。
 *
 * 解析逻辑严格按 SSE 规范：事件以空行分隔，字段格式为 `field: value`，
 * data 多行用 \n 拼接。
 */

export interface SseHandlers {
  /** 每收到一个完整事件调用一次，event 为 `event:` 字段的值（缺省 `message`） */
  onEvent: (event: string, data: unknown) => void;
  onError?: (error: Error) => void;
  onClose?: () => void;
}

interface ParsedBlock {
  event: string;
  data: string;
}

function parseBlock(block: string): ParsedBlock | null {
  let event = "message";
  const dataLines: string[] = [];

  for (const line of block.split("\n")) {
    if (!line || line.startsWith(":")) continue; // 空行与注释行（心跳）跳过
    const colon = line.indexOf(":");
    const field = colon === -1 ? line : line.slice(0, colon);
    let value = colon === -1 ? "" : line.slice(colon + 1);
    if (value.startsWith(" ")) value = value.slice(1);

    if (field === "event") event = value;
    else if (field === "data") dataLines.push(value);
  }

  if (dataLines.length === 0) return null;
  return { event, data: dataLines.join("\n") };
}

export async function streamPost(
  url: string,
  body: unknown,
  handlers: SseHandlers,
  signal?: AbortSignal,
  headers: Record<string, string> = {},
): Promise<void> {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      ...headers,
    },
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok || !response.body) {
    throw new Error(`请求失败：${response.status} ${response.statusText}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;

      // SSE 用 \r\n 分隔，统一成 \n 再切块
      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        const block = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);

        const parsed = parseBlock(block);
        if (parsed) {
          try {
            handlers.onEvent(parsed.event, JSON.parse(parsed.data) as unknown);
          } catch {
            // 单条事件解析失败不应该中断整条流
          }
        }
        boundary = buffer.indexOf("\n\n");
      }
    }
    handlers.onClose?.();
  } catch (error) {
    // 主动取消不算错误
    if (error instanceof Error && error.name === "AbortError") {
      handlers.onClose?.();
      return;
    }
    handlers.onError?.(error instanceof Error ? error : new Error(String(error)));
  }
}