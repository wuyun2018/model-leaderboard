/* 手工维护部分 —— 更新时改这里，不会被 build.py 覆盖
   REAL / DESIGN 的数据来自浏览器抓取（OpenRouter / Design Arena 无公开 API），需手工粘贴
   PICKS 为选型建议，随榜单变化手工调整
   LOCAL 为用户本地已配置模型，改动时同步更新 */

const DATA_DATE = "2026-10-17";

/* ===== 场景速查（手工维护） ===== */
const PICK_CAT = { id:"pick", name:"🎯 场景速查", kind:"pick",
  desc:"别翻榜了，直接按你的活儿挑",
  picks:[
  { task:"日常问答 / 写作 / 翻译", first:"Claude Sonnet 5.5", alt:"Gemini 4 Argon", why:"智能 56 / 52.6，同为 $2/$10，是 Opus 1/5 价的第一梯队" },
  { task:"复杂代码 / 大型重构", first:"Claude Opus 5.5", alt:"GPT-6 Astra", why:"SciCode 66.9% + Terminal-Bench 4.0 59.6%，双料第一" },
  { task:"Agentic 终端 / 自动化脚本", first:"Claude Fable 5.1", alt:"GPT-6 Astra", why:"Terminal-Bench 2.1 拿到 91.4%，断层第一" },
  { task:"长文档分析 / 超长上下文", first:"Kimi K3", alt:"Step 5 Preview", why:"AA-LCR 88.7%，1.05M 上下文，且是开源权重" },
  { task:"图片 / 视频 / 截图理解", first:"Claude Opus 5.5", alt:"GPT-6 Astra", why:"MMMU-Pro 87.7%，多模态断层第一" },
  { task:"数学 / 科学硬推理", first:"GPT-6 Astra", alt:"Claude Opus 5.5", why:"GPQA 96.3%、CritPt 并列第一，理工科最强" },
  { task:"前端页面 / UI 设计生成", first:"Claude Opus 5.5", alt:"GPT-6 Astra", why:"Design Arena Elo 1392，人类偏好第一" },
  { task:"深度研究 / 数据分析报告", first:"Claude Sonnet 5.5", alt:"Claude Fable 5.1", why:"AnalystAgent 57.5%，与 Fable 5.1 并列第一但便宜 5 倍" },
  { task:"运维 / SRE / 排障", first:"Step 5 Preview", alt:"GLM-5.3-Flash", why:"IT-Bench SRE 55.6% 第一，且 $1/$2.7 极便宜" },
  { task:"大批量跑 / 成本敏感", first:"MiMo-V2.6-Flash", alt:"GPT-6 Luna", why:"智能 38，$0.14/$0.28，每任务 $0.06" },
  { task:"实时交互 / 语音助手", first:"Celeris-1", alt:"Mercury 2.5", why:"1459 / 740 tokens每秒，延迟榜前十全是小模型" },
  { task:"私有化 / 本地部署", first:"MiMo-V2.6-Pro", alt:"GLM-5.3", why:"开源综合智能 46 第一，SciCode 60.9% 开源第一" }
]};
