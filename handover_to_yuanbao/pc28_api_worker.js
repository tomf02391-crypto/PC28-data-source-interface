// PC28 对外数据接口 Worker
// 供其他项目仓库/前端调用，返回最新开奖数据，支持 CORS
//
// 数据源优先级：
//   1. GitHub 仓库 data_pc28.json（与推送同源，Actions 每3分钟更新）
//   2. pc28.help 实时接口（兜底）
//
// 部署：Cloudflare Workers 新建 Worker，粘贴本代码即可，无需任何环境变量。

const GH_RAW = "https://raw.githubusercontent.com/tomf02391-crypto/PC28-data-source-interface/main/data_pc28.json";
const PC28_API = "https://pc28.help/api/kj.json";

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  "Cache-Control": "no-store",
};

export default {
  async fetch(request, env, ctx) {
    // 预检请求
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, "") || "/";

    try {
      if (path === "/" || path === "/latest") {
        const item = await fetchLatest();
        if (!item) throw new Error("数据源无数据");
        return json({ code: 0, message: "success", data: item }, CORS_HEADERS);
      }

      if (path === "/history") {
        const limit = Math.min(parseInt(url.searchParams.get("limit") || "1", 10) || 1, 50);
        const items = await fetchHistory(limit);
        return json({ code: 0, message: "success", data: items }, CORS_HEADERS);
      }

      if (path === "/health" || path === "/ping") {
        return json({ code: 0, message: "ok", time: new Date().toISOString() }, CORS_HEADERS);
      }

      return json({ code: 404, message: "Not Found", hint: "可用接口: /latest /history?limit=N /health" }, CORS_HEADERS, 404);
    } catch (e) {
      return json({ code: 500, message: String(e.message || e) }, CORS_HEADERS, 500);
    }
  },
};

async function fetchLatest() {
  // 1. 先试 GitHub 仓库数据
  try {
    const resp = await fetch(GH_RAW, { cf: { cacheTtl: 0 } });
    if (resp.ok) {
      const d = await resp.json();
      if (d && Array.isArray(d.data) && d.data.length > 0) return d.data[0];
    }
  } catch (e) { /* 继续兜底 */ }

  // 2. 兜底 pc28.help
  try {
    const resp = await fetch(`${PC28_API}?t=${Date.now()}`, { cf: { cacheTtl: 0 } });
    if (resp.ok) {
      const d = await resp.json();
      if (d && Array.isArray(d.data) && d.data.length > 0) return d.data[0];
    }
  } catch (e) { /* ignore */ }

  return null;
}

async function fetchHistory(limit) {
  // GitHub 仓库只保留最新一期；如需更多历史可扩展其他源
  const latest = await fetchLatest();
  if (!latest) return [];
  return [latest];
}

function json(obj, headers, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      ...headers,
    },
  });
}
