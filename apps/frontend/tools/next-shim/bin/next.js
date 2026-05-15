#!/usr/bin/env node
"use strict";
// next dev [-p PORT]  -> vite --host [--port PORT]
// next start [-p P]   -> vite preview --host [--port P]
// next build [...]    -> vite build
const { spawnSync } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");
const argv = process.argv.slice(2);
const cmd = argv[0] || "dev";
let port = null;
const rest = [];
for (let i = 1; i < argv.length; i++) {
  const a = argv[i];
  if (a === "-p" || a === "--port") port = argv[++i];
  else if (a.startsWith("--port=")) port = a.slice(7);
  else rest.push(a);
}
const frontendRoot = path.resolve(__dirname, "..", "..", "..");
const viteBin = path.join(
  frontendRoot,
  "node_modules",
  ".bin",
  process.platform === "win32" ? "vite.cmd" : "vite"
);
if (!fs.existsSync(viteBin)) {
  console.error(
    "[next-vite-shim] local vite missing at " +
      viteBin +
      " — run `npm install` in apps/frontend first."
  );
  process.exit(1);
}
let viteArgs;
if (cmd === "build") viteArgs = ["build", ...rest];
else if (cmd === "start")
  viteArgs = ["preview", "--host", ...(port ? ["--port", port] : []), ...rest];
else viteArgs = ["--host", ...(port ? ["--port", port] : []), ...rest];
const res = spawnSync(viteBin, viteArgs, { stdio: "inherit", cwd: frontendRoot });
process.exit(res.status == null ? 1 : res.status);
