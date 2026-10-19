# 部署清单（5 分钟）

## 一、上传哪些文件

必须（少一个页面就白屏或 Actions 失败）：

| 文件 | 作用 | 缺了会怎样 |
|---|---|---|
| `index.html` | 页面骨架 + 渲染逻辑 | 打不开 |
| `manual.js` | 数据日期、场景速查 | 页面报错白屏 |
| `realdata.js` | OpenRouter 用量 / Design Arena | 页面报错白屏 |
| `auto.js` | 9 个基准分类 | 只剩 3 个 tab |
| `fetch_aa.py` | 抓 Artificial Analysis | 每天不更新 |
| `fetch_openrouter.py` | 抓 OpenRouter Data API | 真实用量不更新 |
| `build.py` | 生成 auto.js | 构建失败 |
| `update.sh` | 一键更新 | Actions 跑不起来 |
| `.github/workflows/daily.yml` | 定时任务 | 不会自动跑 |

可选：`README.md`、`.gitignore`、`test_openrouter.py`、`update.ps1`（Windows 本地跑用）

**绝对不要上传**：`.env`（含 API key）、`local.js`（含你的 provider 清单）、`logs/`、`push.sh`

`.gitignore` 已经把这些排除掉了，只要用它就不会误传。

## 二、建仓库并推送

### 方式 A：命令行（推荐）

```bash
cd model-leaderboard
git init
git add -A
git commit -m "init: 全球模型榜单"
git branch -M main
git remote add origin https://github.com/<你的用户名>/model-leaderboard.git
git push -u origin main
```

Windows 用 PowerShell，命令完全一样。

### 方式 B：网页上传

1. GitHub 右上 `+` → New repository → 名字 `model-leaderboard` → **Public** → Create
2. 进入仓库 → `Add file` → `Upload files` → 把 zip 里的文件全选拖进去
3. 注意 `.github/workflows/daily.yml` 要手动建路径：`Add file` → `Create new file`，
   文件名直接输入 `.github/workflows/daily.yml`（斜杠会自动建目录），粘贴内容

> 仓库必须是 **Public**，否则免费账号开不了 GitHub Pages。

## 三、开启 Pages

仓库 → **Settings** → 左侧 **Pages** → Source 选 **GitHub Actions**（不要选 "Deploy from a branch"）

页面地址：`https://<用户名>.github.io/model-leaderboard/`

## 四、加 API Key

仓库 → **Settings** → 左侧 **Secrets and variables** → **Actions** → `New repository secret`

- Name: `OPENROUTER_API_KEY`
- Secret: `sk-or-v1-...`（你的 OpenRouter key）

## 五、手动触发一次验证

仓库 → **Actions** → 左侧 `daily-refresh` → 右侧 `Run workflow` → `Run workflow`

等 1 分钟，绿勾 = 成功。然后刷新页面地址。

以后每天 UTC 22:17（北京时间 06:17）自动跑。

## 六、排错

| 现象 | 原因 | 修法 |
|---|---|---|
| Actions 报 `refusing to allow a Personal Access Token` | 推 workflow 文件缺 scope | token 勾上 `workflow` |
| Actions 红叉在 "Fetch OpenRouter" | Secret 没加或名字拼错 | 必须是 `OPENROUTER_API_KEY` |
| 页面白屏 | 少传了 manual.js / realdata.js / auto.js | 补齐 4 个 js |
| 页面没高亮 | 正常，`local.js` 没上传 | 线上版本来就不显示你的私有模型 |
| Pages 404 | 源选错 | Settings → Pages 改回 GitHub Actions |
| 数据不更新 | Actions 被禁用 | 仓库 60 天无提交会自动停；点 Actions → Enable |
| 本地跑报 `OPENROUTER_API_KEY 未设置` | 没有 `.env` | 建 `.env` 写 `export OPENROUTER_API_KEY=sk-or-v1-...` |

## 七、纯本地方案（不上线）

只想在自己电脑看，跳过前面所有 GitHub 步骤，用这两个脚本：

```sh
./install-schedule.sh          # 装 cron，每天 07:30 自动更新
./install-schedule.sh --run    # 立刻跑一次
./serve.sh                     # 起本地服务器，手机同 Wi-Fi 可看
```

Windows：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File install-schedule.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File install-schedule.ps1 -RunNow
```

更新完直接双击 `index.html` 即可。本地版会显示蓝色高亮（`local.js` 在），线上版不会。

## 七、本地更新（可选）

```bash
export OPENROUTER_API_KEY=sk-or-v1-...   # 或写进 .env
./update.sh          # 抓数据 + 重建页面
./update.sh --push   # 顺带提交推送，Pages 自动重新部署
```

Windows：`powershell -NoProfile -ExecutionPolicy Bypass -File update.ps1`
