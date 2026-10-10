#!/usr/bin/env node
/**
 * 启动后端开发服务（uvicorn --reload）
 *
 * 依次按以下顺序寻找 Python 解释器：
 *   1. 环境变量 AI_COMPANION_PYTHON
 *   2. apps/api/.venv（README 推荐的标准建法）
 *   3. PATH 上的 python / python3
 *
 * 用法：
 *   pnpm dev:api
 *   AI_COMPANION_PYTHON=/path/to/python pnpm dev:api
 */

import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const API_DIR = join(ROOT, "apps", "api");

const PORT = process.env.API_PORT ?? "8000";
const HOST = process.env.API_HOST ?? "127.0.0.1";

/** Windows 用 Scripts/，POSIX 用 bin/ */
function venvPython(venvDir) {
  return process.platform === "win32"
    ? join(venvDir, "Scripts", "python.exe")
    : join(venvDir, "bin", "python");
}

function resolvePython() {
  if (process.env.AI_COMPANION_PYTHON) {
    const custom = process.env.AI_COMPANION_PYTHON;
    if (!existsSync(custom)) {
      fail(`环境变量 AI_COMPANION_PYTHON 指向的解释器不存在：${custom}`);
    }
    return custom;
  }

  const local = venvPython(join(API_DIR, ".venv"));
  if (existsSync(local)) return local;

  const fallback = process.platform === "win32" ? "python" : "python3";
  console.warn(
    [
      "",
      "⚠️  没有找到 apps/api/.venv，将回退到 PATH 上的 `" +
        fallback +
        "`。",
      "   建议按 README 建一个项目虚拟环境，避免装到全局：",
      "     cd apps/api && python -m venv .venv",
      "     .venv/Scripts/pip install -r requirements.txt -r requirements-dev.txt",
      "",
    ].join("\n"),
  );
  return fallback;
}

function fail(msg) {
  console.error(`\n❌ ${msg}\n`);
  process.exit(1);
}

const python = resolvePython();
console.log(`🐍 使用解释器：${python}`);
console.log(`🚀 启动 API：http://${HOST}:${PORT}  (文档 /docs)\n`);

const child = spawn(
  python,
  ["-m", "uvicorn", "app.main:app", "--reload", "--host", HOST, "--port", PORT],
  { cwd: API_DIR, stdio: "inherit", env: process.env },
);

child.on("error", (err) => {
  if (err.code === "ENOENT") {
    fail(
      `找不到解释器 ${python}。\n` +
        `   请先安装依赖：cd apps/api && <你的python> -m pip install -r requirements.txt`,
    );
  }
  fail(err.message);
});

child.on("exit", (code) => process.exit(code ?? 0));

for (const sig of ["SIGINT", "SIGTERM"]) {
  process.on(sig, () => child.kill(sig));
}