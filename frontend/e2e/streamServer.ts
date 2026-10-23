import { createServer, type ServerResponse } from "node:http";
import type { StreamEvent } from "../src/types/chat";

function signal() {
  let resolve!: () => void;
  const promise = new Promise<void>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

/** Real HTTP sockets let the browser consume chunks before the response ends. */
export async function createStreamServer() {
  const streams = new Map<string, ReturnType<typeof reserve>>();
  let sequence = 0;
  const server = createServer((request, response) => {
    response.setHeader("Access-Control-Allow-Origin", "*");
    response.setHeader("Access-Control-Allow-Headers", "content-type");
    response.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
    if (request.method === "OPTIONS") {
      response.writeHead(204).end();
      return;
    }
    const stream = streams.get(request.url ?? "");
    if (!stream || request.method !== "POST") {
      response.writeHead(404).end();
      return;
    }
    request.resume();
    stream.attach(response);
  });
  await new Promise<void>((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  const address = server.address();
  if (!address || typeof address === "string") throw new Error("Missing stream fixture port");
  const origin = `http://127.0.0.1:${address.port}`;

  function reserve() {
    const path = `/stream-${++sequence}`;
    const connected = signal(),
      closed = signal();
    let response: ServerResponse | undefined;
    let ended = false;
    let completed = false;
    const stream = {
      url: origin + path,
      get completed() {
        return completed;
      },
      connected: connected.promise,
      closed: closed.promise,
      onEvent: (_event: StreamEvent) => {},
      onClose: () => {},
      attach(res: ServerResponse) {
        response = res;
        res.writeHead(200, { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" });
        res.flushHeaders();
        res.on("close", () => {
          ended = true;
          stream.onClose();
          closed.resolve();
        });
        connected.resolve();
      },
      write(chunk: string | Uint8Array) {
        if (!response || ended) throw new Error("Stream must be connected and open before writing");
        response.write(chunk);
      },
      send(event: StreamEvent) {
        stream.write(`data: ${JSON.stringify(event)}\n\n`);
        stream.onEvent(event);
      },
      finish() {
        stream.write("data: [DONE]\n\n");
        completed = true;
        response!.end();
      },
      disconnect() {
        response?.destroy();
      },
    };
    streams.set(path, stream);
    return stream;
  }
  return {
    reserve,
    async dispose() {
      for (const stream of streams.values()) stream.disconnect();
      server.closeAllConnections();
      await new Promise<void>((resolve, reject) =>
        server.close((error) => (error ? reject(error) : resolve())),
      );
    },
  };
}
