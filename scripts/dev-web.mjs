#!/usr/bin/env node
/**
 * 启动前端开发服务（next dev）
 *
 * 刻意不依赖 pnpm / npm：直接用当前 Node 去跑 apps/web 里的 next 入口，
 * 这样在 PowerShell、cmd、Git Bash 下都能用 `node scripts/dev-web.mjs` 启动，
 * 也不会因为「某个 shell 里没装 pnpm」而起不来。
 *
 * 前置条件：已经装过依赖
 *   npm install          # 或 pnpm install / corepack pnpm install
 */

import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const WEB_DIR = join(ROOT, "apps", "web");
const NEXT_BIN = join(WEB_DIR, "node_modules", "next", "dist", "bin", "next");

const PORT = process.env.PORT ?? "3000";

if (!existsSync(NEXT_BIN)) {
  console.error(
    [
      "",
      "❌ 找不到 Next.js：",
      `   ${NEXT_BIN}`,
      "",
      "   说明前端依赖还没装。先在项目根目录执行：",
      "     npm install",
      "     # 或：corepack pnpm install",
      "",
    ].join("\n"),
  );
  process.exit(1);
}

console.log(`▲ Next.js 开发服务器：http://localhost:${PORT}\n`);

const child = spawn(process.execPath, [NEXT_BIN, "dev", "-p", PORT], {
  cwd: WEB_DIR,
  stdio: "inherit",
  env: process.env,
});

child.on("error", (err) => {
  console.error(`\n❌ 启动失败：${err.message}\n`);
  process.exit(1);
});

child.on("exit", (code) => process.exit(code ?? 0));

for (const sig of ["SIGINT", "SIGTERM"]) {
  process.on(sig, () => child.kill(sig));
}