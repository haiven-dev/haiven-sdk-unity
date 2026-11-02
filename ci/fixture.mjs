import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { resolve, extname, sep } from "node:path";
import { WebSocketServer } from "ws";
const root = resolve(process.env.HAIVEN_WEBGL_OUTPUT);
const stats = { connections: 0, roundTrips: 0, closed: 0, exchanges: 0, lastExchange: null };
const server = createServer(async (req, res) => {
  if (req.url === "/stats") { res.setHeader("Content-Type", "application/json"); res.end(JSON.stringify(stats)); return; }
  if (req.url === "/v0/auth/handoff/exchange" && req.method === "POST") {
    let body = "";
    for await (const chunk of req) body += chunk;
    const fields = new URLSearchParams(body);
    const names = [...fields.keys()].sort();
    const exchange = Object.fromEntries(fields);
    const valid = (req.headers["content-type"] ?? "").split(";", 1)[0].trim() === "application/x-www-form-urlencoded"
      && JSON.stringify(names) === JSON.stringify(["code", "code_verifier", "integration_id", "redirect_uri"])
      && exchange.code === "webgl-code"
      && /^[A-Za-z0-9_-]{43}$/.test(exchange.code_verifier ?? "")
      && exchange.integration_id === "webgl-smoke"
      && exchange.redirect_uri === "http://127.0.0.1:18765/callback?mode=login";
    if (!valid) { res.statusCode = 400; res.end(JSON.stringify({code:"invalid_handoff_request"})); return; }
    stats.exchanges++;
    stats.lastExchange = {code:exchange.code, integration_id:exchange.integration_id, redirect_uri:exchange.redirect_uri, keys:names};
    res.setHeader("Content-Type", "application/json");
    res.setHeader("Cache-Control", "no-store");
    res.end(JSON.stringify({access_token:"webgl-access", token_type:"Bearer", expires_in:300}));
    return;
  }
  try {
    const pathname = decodeURIComponent(new URL(req.url, "http://localhost").pathname);
    const file = resolve(root, "." + (pathname === "/" ? "/index.html" : pathname));
    if (!file.startsWith(root + sep)) throw new Error("outside build");
    res.setHeader("Content-Type", ({".wasm":"application/wasm", ".js":"application/javascript", ".html":"text/html"})[extname(file)] ?? "application/octet-stream");
    res.end(await readFile(file));
  } catch { res.statusCode = 404; res.end("not found"); }
});
const sockets = new WebSocketServer({ server, path: "/socket" });
sockets.on("connection", socket => {
  stats.connections++;
  socket.send(JSON.stringify({type:"ready",success:true}));
  socket.on("message", (bytes, binary) => {
    if (binary) return;
    if (bytes.toString() === "haiven-π") stats.roundTrips++;
    socket.send(bytes.toString());
  });
  socket.on("close", () => { stats.connections--; stats.closed++; });
});
server.listen(18765, "127.0.0.1", () => console.log("HAIVEN_FIXTURE_READY"));
