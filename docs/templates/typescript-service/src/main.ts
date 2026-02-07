/**
 * {{SERVICE_NAME}} - Main Application Entry Point
 *
 * A simple HTTP service built with TypeScript.
 */

import { createServer, IncomingMessage, ServerResponse } from "http";

const PORT = process.env.PORT || 8080;

interface JsonResponse {
  [key: string]: string;
}

function sendJson(res: ServerResponse, status: number, data: JsonResponse): void {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(data));
}

function handleRequest(req: IncomingMessage, res: ServerResponse): void {
  const url = req.url || "/";

  if (url === "/healthz") {
    sendJson(res, 200, { status: "healthy" });
  } else if (url === "/ready") {
    sendJson(res, 200, { status: "ready" });
  } else if (url === "/") {
    sendJson(res, 200, { service: "{{SERVICE_NAME}}", status: "running" });
  } else {
    sendJson(res, 404, { error: "not found" });
  }
}

const server = createServer(handleRequest);

server.listen(PORT, () => {
  console.log(`Starting {{SERVICE_NAME}} on port ${PORT}`);
});

export { handleRequest, sendJson };
