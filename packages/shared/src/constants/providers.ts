/**
 * 模型服务商目录。
 *
 * 前端设置页用它渲染下拉与表单提示，后端用它校验「这个 provider 该读哪个环境变量」。
 * 新增服务商时只改这里一处。
 */

export interface ModelProvider {
  /** LiteLLM provider 前缀，如 deepseek / dashscope */
  id: string;
  /** 界面展示名 */
  label: string;
  /** 该服务商的环境变量名 */
  envKey: string;
  /** 建议的模型 id（可填在请求里） */
  defaultModel: string;
  /** 常用模型列表 */
  models: string[];
  /** 是否有免费/低价额度，用于在界面上提示 */
  freeTier?: boolean;
  /** 官方控制台地址 */
  consoleUrl?: string;
  /** Key 的典型格式，用于前端做格式校验 */
  keyHint: string;
}

export const MODEL_PROVIDERS: ModelProvider[] = [
  {
    id: "deepseek",
    label: "DeepSeek",
    envKey: "DEEPSEEK_API_KEY",
    defaultModel: "deepseek-chat",
    models: ["deepseek-chat", "deepseek-reasoner"],
    freeTier: true,
    consoleUrl: "https://platform.deepseek.com/",
    keyHint: "sk- 开头",
  },
  {
    id: "dashscope",
    label: "阿里云百炼（通义千问）",
    envKey: "DASHSCOPE_API_KEY",
    defaultModel: "qwen-plus",
    models: ["qwen-plus", "qwen-turbo", "qwen-max", "text-embedding-v3"],
    consoleUrl: "https://bailian.console.aliyun.com/",
    keyHint: "sk- 开头",
  },
  {
    id: "openai",
    label: "OpenAI",
    envKey: "OPENAI_API_KEY",
    defaultModel: "gpt-4o-mini",
    models: ["gpt-4o-mini", "gpt-4o", "gpt-4o-mini-embedding"],
    consoleUrl: "https://platform.openai.com/",
    keyHint: "sk- 开头",
  },
  {
    id: "anthropic",
    label: "Anthropic Claude",
    envKey: "ANTHROPIC_API_KEY",
    defaultModel: "claude-3-5-sonnet-latest",
    models: ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest"],
    consoleUrl: "https://console.anthropic.com/",
    keyHint: "sk-ant- 开头",
  },
  {
    id: "gemini",
    label: "Google Gemini",
    envKey: "GEMINI_API_KEY",
    defaultModel: "gemini-2.0-flash",
    models: ["gemini-2.0-flash", "gemini-1.5-pro"],
    consoleUrl: "https://aistudio.google.com/",
    keyHint: "AIza 开头",
  },
  {
    id: "siliconflow",
    label: "硅基流动",
    envKey: "SILICONFLOW_API_KEY",
    defaultModel: "Qwen/Qwen2.5-7B-Instruct",
    models: ["Qwen/Qwen2.5-7B-Instruct", "BAAI/bge-m3"],
    consoleUrl: "https://cloud.siliconflow.cn/",
    keyHint: "sk- 开头",
  },
  {
    id: "moonshot",
    label: "Moonshot 月之暗面",
    envKey: "MOONSHOT_API_KEY",
    defaultModel: "moonshot-v1-8k",
    models: ["moonshot-v1-8k", "moonshot-v1-32k"],
    consoleUrl: "https://platform.moonshot.cn/",
    keyHint: "sk- 开头",
  },
  {
    id: "zhipu",
    label: "智谱 GLM",
    envKey: "ZHIPUAI_API_KEY",
    defaultModel: "glm-4-flash",
    models: ["glm-4-flash", "glm-4-plus"],
    consoleUrl: "https://open.bigmodel.cn/",
    keyHint: "id.secret 格式",
  },
  {
    id: "ollama",
    label: "Ollama 本地模型",
    envKey: "",
    defaultModel: "ollama/qwen2.5:7b",
    models: ["ollama/qwen2.5:7b", "ollama/llama3.1:8b"],
    consoleUrl: "https://ollama.com/",
    keyHint: "本地模型无需填写 Key",
  },
];

export function providerById(id: string): ModelProvider | undefined {
  return MODEL_PROVIDERS.find((p) => p.id === id);
}