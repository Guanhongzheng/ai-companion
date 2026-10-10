#!/usr/bin/env node
/**
 * 启动网易云音乐 API（NeteaseCloudMusicApi Enhanced）本地服务。
 *
 * 这是一个**独立于本仓库的第三方服务**，需要先单独准备源码：
 *
 *   git clone --depth 1 https://github.com/neteasecloudmusicapienhanced/api-enhanced.git
 *   cd api-enhanced && npm install --ignore-scripts
 *
 * 默认在 ../../tools/api-enhanced 找它，找不到就用环境变量指定：
 *   AI_COMPANION_MUSIC_DIR=/path/to/api-enhanced npm run dev:music
 *
 * 与 dev-api.mjs / dev-web.mjs 一样，不依赖 pnpm，任何终端都能跑。
 */

import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const PORT = process.env.MUSIC_PORT ?? "3001";

const candidates = [
  process.env.AI_COMPANION_MUSIC_DIR,
  join(ROOT, "..", "tools", "api-enhanced"),
  join(homedir(), "tools", "api-enhanced"),
].filter(Boolean);

const serviceDir = candidates.find((dir) => existsSync(join(dir, "app.js")));

if (!serviceDir) {
  console.error(
    [
      "",
      "❌ 找不到网易云音乐 API 服务源码。",
      "",
      "   请先克隆并安装依赖：",
      "     git clone --depth 1 https://github.com/neteasecloudmusicapienhanced/api-enhanced.git",
      "     cd api-enhanced && npm install --ignore-scripts",
      "",
      "   装好后把它放在 ../../tools/api-enhanced，或用环境变量指定路径：",
      "     AI_COMPANION_MUSIC_DIR=/你的路径 npm run dev:music",
      "",
      "   注意：这是可选功能，不启动它不影响对话、情绪识别与粒子壁纸。",
      "",
    ].join("\n"),
  );
  process.exit(1);
}

console.log(`🎵 服务目录：${serviceDir}`);
console.log(`🎵 启动音乐 API：http://localhost:${PORT}\n`);

// 这套服务内部用的 HTTP 客户端会读取代理环境变量，
// 指向不可用的代理会导致所有请求失败，所以这里显式清空。
const env = { ...process.env, PORT, CORS_ALLOW_ORIGIN: "*" };
for (const key of ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "no_proxy", "NO_PROXY"]) {
  delete env[key];
}

const child = spawn(process.execPath, ["app.js"], {
  cwd: serviceDir,
  stdio: "inherit",
  env,
});

child.on("error", (err) => {
  console.error(`\n❌ 启动失败：${err.message}\n`);
  process.exit(1);
});

child.on("exit", (code) => process.exit(code ?? 0));

for (const sig of ["SIGINT", "SIGTERM"]) {
  process.on(sig, () => child.kill(sig));
}