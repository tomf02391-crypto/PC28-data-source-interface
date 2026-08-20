# 给元宝的读取指令 + 所需 Token 清单

> 本文件由老板（马尾丝）整理，供元宝 AI 接手 PC28 项目时直接读取使用。
> 生成日期：2026-08-20

---

## 一、项目交接包在仓库的位置

所有交接文件已上传到仓库独立目录 **`handover_to_yuanbao/`**，与项目运行文件（fetch_and_push.py、assets/、data_pc28.json 等）完全分开，不会混淆。

仓库地址：https://github.com/tomf02391-crypto/PC28-data-source-interface

交接目录内容：

| 文件 | 说明 |
|------|------|
| `handover_to_yuanbao/PC28项目交接文档.md` | 完整交接文档（含第九章完整权限清单） |
| `handover_to_yuanbao/PC28接口接入指南.md` | 各语言接入 data_pc28.json 的教程 |
| `handover_to_yuanbao/fetch_and_push_hd.py` | 主脚本 v4 高清版（370 行） |
| `handover_to_yuanbao/pc28_api_worker.js` | Cloudflare Worker 脚本 |
| `handover_to_yuanbao/assets/` | 高清底图 + 字符库（冬/夏两套） |

---

## 二、元宝读取步骤（直接照做）

1. 打开仓库：https://github.com/tomf02391-crypto/PC28-data-source-interface
2. 进入 `handover_to_yuanbao/` 目录
3. 先读 `PC28项目交接文档.md`（含全部权限信息）
4. 需要代码时读 `fetch_and_push_hd.py` 和 `pc28_api_worker.js`
5. 需要对外接口时读 `PC28接口接入指南.md`

> 注：元宝若无法直接访问 GitHub 网页，可让老板把 `handover_to_yuanbao/` 目录内容贴出，或用 raw 链接读取：
> `https://raw.githubusercontent.com/tomf02391-crypto/PC28-data-source-interface/main/handover_to_yuanbao/PC28项目交接文档.md`

---

## 三、所需 Token 与权限清单（元宝接手需持有）

### GitHub
- 账号：`tomf02391-crypto`
- 仓库：`PC28-data-source-interface`
- **GitHub Token**：`{{GITHUB_TOKEN}}`
- Token 权限：Fine-grained，Actions Read/Write，仅限本仓库
- 仓库 Secrets（Settings → Secrets and variables → Actions）：
  - `TG_BOT_TOKEN`：Telegram Bot Token（值在 BotFather 可查/重置）
  - `TG_CHANNEL_ID`：`@pc28jndkj`
  - `TG_GROUP_ID`：已配置（群组文字推送）
  - `YU28_API_KEY`：`{{YU28_API_KEY}}`

### Cloudflare Worker
- 账号：老板的 Cloudflare 账号
- Account ID：`5c6b58732cfaee64256c751689c66d42`
- Worker 名称：`pc28trigger`
- Worker 域名：`azj0834.workers.dev`
- Cron：`*/3 * * * *`（每 3 分钟）
- **CF API Token**：`{{CLOUDFLARE_TOKEN}}`
- 控制台：https://dash.cloudflare.com → Workers & Pages → pc28trigger
- Worker 环境变量：
  - `GH_TOKEN`：同上 GitHub Token（Secret）
  - `GH_REPO`：`tomf02391-crypto/PC28-data-source-interface`
  - `GH_WORKFLOW`：`fetch-pc28.yml`

### Telegram
- 频道：`@pc28jndkj`（图片推送）
- 群组：`wyjtpc28a`（可选文字推送）
- Bot Token：在 GitHub Secrets `TG_BOT_TOKEN` 中

### 数据源 API
- 主源 pc28.help：`https://pc28.help/api/kj.json?t=时间戳`（无需密钥）
- 备用 yu28.top：`https://yu28.top/api/kj.json?t=时间戳`
  - 密钥：`{{YU28_API_KEY}}`
  - 调用方式：必须用请求头 `X-Api-Key: {{YU28_API_KEY}}` 传递，URL 参数方式无效

---

## 四、安全提醒

⚠️ 以上 Token 均为历史会话中老板提供，明文已出现在聊天记录。
**建议交接完成后，在 GitHub / Cloudflare 控制台重新生成一轮 Token**，避免泄露风险。

---

*元宝按本文件即可独立读取项目、运行与维护。*