/**
 * 网易云音乐 API（NeteaseCloudMusicApi Enhanced）封装。
 *
 * 该服务需要单独启动，本项目用 docker compose 的 `infra` profile 提供：
 *   docker compose --profile infra up -d music-api
 *
 * 服务没起时所有方法都会 reject，由 store 统一降级为提示态，不会白屏。
 */

const BASE_URL = (
  process.env.NEXT_PUBLIC_MUSIC_API_BASE_URL ?? "http://localhost:3001"
).replace(/\/$/, "");

export interface Track {
  id: number;
  name: string;
  artist: string;
  album: string;
  durationMs: number;
  url: string | null;
}

interface RawSong {
  id: number;
  name: string;
  ar?: Array<{ name: string }>;
  al?: { name: string };
  dt?: number;
  /** Enhanced 版可能直接带 url，网易官方接口通常不带 */
  url?: string | null;
}

function toTrack(song: RawSong): Track {
  return {
    id: song.id,
    name: song.name,
    artist: (song.ar ?? []).map((a) => a.name).join(" / ") || "未知歌手",
    album: song.al?.name ?? "",
    durationMs: song.dt ?? 0,
    url: song.url ?? null,
  };
}

async function get<T>(path: string, params: Record<string, string | number>): Promise<T> {
  const url = new URL(`${BASE_URL}${path}`);
  for (const [k, v] of Object.entries(params)) url.searchParams.set(k, String(v));

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 8000);
  try {
    const resp = await fetch(url.toString(), { signal: controller.signal });
    if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`);
    return (await resp.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

export const musicApi = {
  async health(): Promise<boolean> {
    try {
      const resp = await fetch(`${BASE_URL}/login/status`, {
        signal: AbortSignal.timeout(3000),
      });
      return resp.ok;
    } catch {
      return false;
    }
  },

  async search(keywords: string, limit = 12): Promise<Track[]> {
    const data = await get<{ result?: { songs?: RawSong[] } }>("/cloudsearch", {
      keywords,
      type: 1,
      limit,
    });
    return (data.result?.songs ?? []).map(toTrack);
  },

  async songUrl(id: number): Promise<string | null> {
    const data = await get<{ data?: Array<{ url?: string | null }> }>("/song/url", { id });
    return data.data?.[0]?.url ?? null;
  },
};

export const MUSIC_API_BASE_URL = BASE_URL;