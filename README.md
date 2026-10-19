# 全球模型排行榜（按用途分类）

数据日期 **2026-10-17** · [打开榜单页](index.html)

## 一键更新

```bash
cd model-leaderboard
python3 fetch_aa.py     # 抓 Artificial Analysis（700+ 模型 × 48 指标）
python3 build.py        # 重新生成全部自动榜单 + 刷新浏览器缓存版本号
```

刷一下页面就是最新的。OpenRouter 和 Design Arena 的数据靠浏览器渲染，需要人工抓后更新 `manual.js`（见下）。

## 文件说明

| 文件 | 作用 |
|---|---|
| `index.html` | 榜单页面（12 个分类 tab，自动高亮你本地已配置的模型） |
| `manual.js` | **手工维护**：场景速查、OpenRouter 真实用量、Design Arena、你的本地模型清单 |
| `auto.js` | **自动生成**，勿手改。由 `build.py` 从 `aa_models_raw.json` 生成 |
| `aa_models_raw.json` | Artificial Analysis 原始数据（703 条，含 431 条已下架） |
| `fetch_aa.py` | 抓取 + 解析 AA 页面 |
| `build.py` | 生成 `auto.js` + 刷新 `index.html` 里的 `?v=` 缓存版本号 |
| `query.py` | 命令行查询任意指标 |
| `rank2.py` / `parse_aa.py` | 早期脚本，保留备用 |

## 数据源

- **Artificial Analysis** `artificialanalysis.ai/leaderboards/models` —— 综合智能指数 + 编程 / Agent / 长文本 / 多模态 / 推理 / 幻觉 / 速度 / 延迟 / 成本，共 48 个字段
- **OpenRouter** `openrouter.ai/rankings` —— 真实 token 用量（周榜 / 日榜 / 增长榜 / 厂商份额 / 热门 Agent 应用）
- **Design Arena** `designarena.ai/leaderboard` —— 人类盲测 Elo（前端 / 设计）
- ~~LMArena~~ —— 当前网络环境完全不可达（curl HTTP 000，浏览器 ERR_CONNECTION_TIMED_OUT）

## 数据处理规则（build.py）

1. **每模型只保留最高推理档位** —— 同一模型的 (Max)/(Xhigh)/(High) 会被去重成一个，避免刷屏
2. **低幻觉率榜限智能 ≥30** —— 否则 3B 小模型会因为"不敢回答"而刷榜
3. **延迟榜只统计非推理模型** —— 推理模型的 TTFT 包含思考时间（Claude Opus 5.5 Max 高达 666 秒），混进来没有可比性
4. **成本榜限智能 ≥30** —— 同理，避免拿没法用的模型比价格

## 命令行查询

```bash
python3 query.py top scicode 10          # 按任意字段取前 10
python3 query.py top scicode 10 open     # 只看开源模型
python3 query.py show "Kimi K3"          # 看单个模型全部指标
python3 query.py fields                  # 列出所有可用字段
python3 query.py cheap 20                # 高智能低成本
```

字段名直接对应 AA 原始 JSON：`intelligenceIndex` `scicode` `terminalBench21` `terminalBench40` `tau2` `tauBanking` `apexAgents` `analystAgent` `itbenchSre` `lcr` `hle` `gpqa` `critpt` `ifbench` `mmmuPro` `gdpvalNormalized` `omniscience` `omniscienceNonHallucination` `medianOutputTokensPerSecond` `medianTimeToFirstTokenSeconds` `intelligenceIndexCostPerTask` 等。

## 文件分工

| 文件 | 谁写 | 说明 |
|---|---|---|
| `index.html` | 手改 | 页面骨架 + 渲染逻辑 |
| `manual.js` | 手改 | `DATA_DATE`、场景速查 `PICK_CAT` |
| `realdata.js` | **自动** `fetch_openrouter.py` | OpenRouter 用量 / Design Arena Elo / 会话成本 / 任务结构；无 key 时保留上次内容 |
| `.env` | 手建，**不入库** | `OPENROUTER_API_KEY=...`，`update.sh` 自动 source |
| `auto.js` | **自动** `build.py` | 9 个基准分类 |
| `local.js` | 手改，**不入库** | 你在各 provider 的模型清单，用于蓝色高亮；缺失时页面自动降级为无高亮 |

`auto.js` / `realdata.js` 不要手改，会被覆盖。

## 一键更新

```sh
./update.sh            # Linux / macOS / 沙箱
./update.sh --push     # 顺带 git 提交并推送
```
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File update.ps1       # Windows
powershell -NoProfile -ExecutionPolicy Bypass -File update.ps1 -Push
```

日志写在 `logs/update-*.log`，保留最近 30 份。`fetch_aa.py` 每次强制重新下载（重试 3 次、体积校验、解析数 <100 则拒绝覆盖），不会像旧版那样复用 `/tmp` 的陈旧 HTML。

## OpenRouter Data API（关键）

之前的判断是「OpenRouter / Design Arena 没有公开 API，只能浏览器抓」，**这个结论是错的**。官方有 Data API，只是必须带 key：

```
GET /api/v1/datasets/rankings-daily?start_date=&end_date=   每日 top50 模型 token 量
GET /api/v1/datasets/app-rankings?sort=popular&limit=10     应用榜
GET /api/v1/datasets/session-cost?app_slug=&turn_range=     每次会话花费中位数（周更新）
GET /api/v1/benchmarks?source=design-arena&arena=models&category=codecategories
GET /api/v1/benchmarks?source=artificial-analysis           AA 综合分（仅 3 个指纹，无细分指标）
GET /api/v1/classifications/task?window=7d                  流量按任务的份额（抽样）
GET /api/v1/models                                          公开目录，免 key，用于 slug→显示名
```

`rankings-daily` 还有四个文档正文没列全的参数：`period`（day/week/month）、`modality`、`context_bucket`（1K/10K/100K/1M/10M）、`category` / `language_type`。后两者是**抽样上采样估算值**且按周聚合，不能与 `modality`、`context_bucket` 同用（会 400）。

鉴权 `Authorization: Bearer $OPENROUTER_API_KEY`，限速 30 次/分、500 次/天。数据许可 CC BY 4.0，转载需带 `Source: OpenRouter (openrouter.ai/rankings) as of <meta.as_of>`。

设置 key（三选一）：
- 项目根目录 `.env`：`export OPENROUTER_API_KEY=sk-or-v1-...`（**推荐**，`update.sh` 自动加载，已在 `.gitignore`）
- 环境变量 `OPENROUTER_API_KEY`
- GitHub 仓库 Secrets（Actions 用，变量名 `OPENROUTER_API_KEY`）

没有 key 时 `fetch_openrouter.py` 打印提示后退出 0，**不改动** `realdata.js` —— 也就是说手工维护的路径始终可用，两者不冲突。

「真实用量」tab 的分组会自动伸缩：`REAL.sessions` / `tasks` / `coding` / `longctx` 为空时，`build.py` 生成的 `groups` 会被 `.filter(g => g.rows.length)` 摘掉。无 key → 5 组；有 key → 9 组。

AA 的细分指标（`scicode` / `gpqa` / `lcr` / `itbenchSre`…）**Data API 不提供**，仍靠 `fetch_aa.py` 解析页面 RSC payload。这是整条链路里唯一还在依赖页面结构的地方，页面改版会断——所以脚本做了「解析数 <100 就拒绝覆盖」的保护。

## 部署

纯静态，四个文件（`index.html` `manual.js` `realdata.js` `auto.js`），无后端、无构建依赖。

**方案 A · GitHub Pages + Actions（推荐，完全无值守）**

1. 建仓库，推上去
2. Settings → Secrets → 新增 `OPENROUTER_API_KEY`
3. Settings → Pages → Source 选 **GitHub Actions**
4. 已带 `.github/workflows/daily.yml`：每天 UTC 23:00（北京 07:00）抓数据 → 提交 → 发布

产物只包含 4 个静态文件，`local.js` 不会上传（`.gitignore` 已排除），页面自动无高亮、不泄露你的 provider 清单。

**方案 B · Cloudflare Pages / Netlify（CDN 更快）**

连接同一个仓库，构建命令留空、输出目录填 `/`。数据由 Actions 提交进仓库，平台检测到 commit 自动重新部署。也可以本地跑 `update.sh --push` 直接推。

**方案 C · 自有 VPS（完全掌控）**

```sh
# nginx 指向项目目录，然后 crontab
17 6 * * * cd /srv/leaderboard && ./update.sh >> logs/cron.log 2>&1
```

**方案 D · 只看不发布**

直接浏览器打开 `index.html`，或 `python3 -m http.server 8080` 走局域网。手机同网段访问 `http://<电脑IP>:8080`。

## 纯本地方案（不上线，只自己看）

不想公开、也不想要 GitHub，就只在本机跑：

```sh
./install-schedule.sh              # 装 cron，每天 07:30
./install-schedule.sh 08:15        # 指定时间
./install-schedule.sh --run        # 立即跑一次
./install-schedule.sh --remove     # 卸载
./install-schedule.sh --dry-run    # 只打印将写入的 crontab
./serve.sh 8080                    # 本地预览，手机同 Wi-Fi 可看
```

Windows：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File install-schedule.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File install-schedule.ps1 -Time 08:15
powershell -NoProfile -ExecutionPolicy Bypass -File install-schedule.ps1 -RunNow
powershell -NoProfile -ExecutionPolicy Bypass -File install-schedule.ps1 -Remove
powershell -NoProfile -ExecutionPolicy Bypass -File install-schedule.ps1 -Serve   # 顺带起服务器
```

看页面三种方式，从简到繁：

1. 双击 `index.html` —— 最省事，file:// 直接可读
2. `./serve.sh` —— 手机/平板同网段访问，`http://<电脑IP>:8080`
3. `python3 -m http.server 8080` 然后浏览器打开 `http://localhost:8080`

**和线上版的唯一区别**：本地会显示蓝色高亮（`local.js` 在），线上不会。

代价：电脑必须开机且不睡眠，cron/计划任务才会触发。要真正无人值守，还是上 GitHub Actions。

## 定时更新

| 场景 | 做法 | 可靠性 |
|---|---|---|
| 云端 | GitHub Actions cron | 最高，不依赖你的设备开机 |
| Windows | 计划任务 → `update.ps1` | 高，需开机 |
| macOS/Linux | crontab → `update.sh` | 高，需开机 |
| 第三方客户端 | 若其自动化能执行命令，指向 `update.ps1` | 中，客户端退出即停 |
| 移动端/桌面端定时能力 | 用系统自带的定时功能调用同一脚本 | 中，依赖设备在线 |

Windows 计划任务（管理员 cmd）：

```cmd
schtasks /Create /TN "ModelLeaderboard" /TR "powershell -NoProfile -ExecutionPolicy Bypass -File D:\leaderboard\update.ps1" /SC DAILY /ST 07:30 /F
```

改完想立刻验一次：`schtasks /Run /TN "ModelLeaderboard"`，然后看 `logs\update-*.log`。
