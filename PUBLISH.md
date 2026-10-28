# GitHub 发布清单

这份文档是给你自己用的：把占位符替换掉，然后按顺序发。

---

## 1. 发布前替换

在以下文件里把 `SuHoKUO` 换成你的 GitHub 用户名：

- `metadata.yaml`：`author`、`repo`
- `README.md`：Releases 链接
- `PUBLISH.md`：本文件里的示例链接

建议同时确认：

- [ ] `metadata.yaml` 的 `name` 与目录名一致：`astrbot_plugin_companion_admin`
- [ ] 没有把作者的个人 QQ 号写进发布版代码/默认配置（发布版已移除）
- [ ] 没有 `data/`、`backups/`、`audit.jsonl`、`__pycache__`
- [ ] 没有 API Key、Cookie、JWT secret
- [ ] `main.py` 能通过 `py_compile`
- [ ] 用干净环境安装一次 ZIP，确认能加载

---

## 2. 仓库信息

**仓库名**

```text
astrbot_plugin_companion_admin
```

**About 短描述（<= 350 字符）**

```text
让 AstrBot 陪伴类 Bot 在管理员私聊里用自然语言修改自己的人格、用户风格、群白名单和 TTS。所有写入先提案、确认后执行，并带快照、审计和回滚。AstrBot >= 4.22。
```

**Topics**

```text
astrbot
astrbot-plugin
qq-bot
ai-companion
self-management
persona
tts
python
```

**Release 标题**

```text
v0.1.0 — 陪伴自我管理
```

---

## 3. 推送到 GitHub

先在 GitHub 创建一个**空仓库**（不要勾选 README / .gitignore / license），然后：

```bash
cd astrbot_plugin_companion_admin

git init
git add .
git commit -m "feat: initial release v0.1.0"
git branch -M main
git remote add origin https://github.com/<SuHoKUO>/astrbot_plugin_companion_admin.git
git push -u origin main

git tag v0.1.0
git push origin v0.1.0
```

然后在 GitHub：

1. Releases → Draft a new release；
2. 选择 tag `v0.1.0`；
3. 标题填 `v0.1.0 — 陪伴自我管理`；
4. 正文复制下面「Release 正文」；
5. 上传 `astrbot_plugin_companion_admin-0.1.0.zip`；
6. 勾选 `Set as the latest release`；
7. 发布。

---

## 4. Release 正文

```markdown
# 陪伴自我管理 v0.1.0

让陪伴类 Bot 在管理员私聊里，用自然语言查看和修改**自己的人格、用户风格、群白名单和 TTS**。

所有写入先提案、确认后执行，并带快照、审计和回滚。

## 功能

- 管理员门禁：只认 `sender_id`，仅私聊
- 只读诊断：人格段落、TTS、群白名单、待确认修改
- 日志查看：最近后端日志，自动脱敏
- 人格段落修改：按 `【段落】` 替换/追加
- 用户风格/称呼修改
- 群白名单加/删/切换
- TTS 开关、Provider、触发概率、发送形态
- 提案 → 确认 → 写入；未确认不落盘
- 快照 / 回滚 / 审计

## 安装

1. 下载 `astrbot_plugin_companion_admin-0.1.0.zip`
2. AstrBot Dashboard → 插件 → 安装 → 上传 ZIP
3. 启用插件
4. 在插件配置里填写 `admin_ids`（至少一个你的 QQ 号）
5. 用管理员账号私聊 Bot，说「查一下你自己的状态」

## 配置

| 配置 | 默认 | 说明 |
| --- | --- | --- |
| `admin_ids` | `[]` | 允许使用自我管理的用户 ID；也可用 AstrBot `admins_id` |
| `persona_id` | `大肥鱼` | 要管理的人格 ID |
| `companion_plugin` | `astrbot_plugin_private_companion` | 陪伴插件目录名 |

## 安全

- 仅管理员私聊；群聊不开放
- 提案与确认分离，未确认不写入
- 写入前快照，支持回滚
- 不暴露 Key；日志脱敏
- 不能改管理员列表、凭据、安全门禁或插件自身代码

## 限制

- 需要主模型支持 tool calling
- 修改风格/白名单/TTS 会重载陪伴插件，当前轮可能短暂中断
- 仅配置/人格层，不含代码级自我修改

## 兼容

AstrBot >= 4.22；已在 AstrBot 4.29.3 + `astrbot_plugin_private_companion` 6.5.6 验证。

## License

MIT
```

---

## 5. 社媒/群聊文案

### QQ 群 / 频道（完整版）

```text
整了个新插件：陪伴自我管理（astrbot_plugin_companion_admin）

简单说，就是让你的陪伴 Bot 在私聊里“自己改自己”：
- 改人格的某个段落，不用整份重写
- 改某个用户的称呼/风格
- 加/删群白名单
- 改 TTS 开关、Provider、触发概率

关键是安全：她不会直接写，而是先给你看改动，你回“确认”才落盘；改前有快照，改坏了能回滚。

需要 AstrBot >= 4.22，配合 astrbot_plugin_private_companion 用。
仓库：https://github.com/SuHoKUO/astrbot_plugin_companion_admin
Release：https://github.com/SuHoKUO/astrbot_plugin_companion_admin/releases/tag/v0.1.0
```

### B 站动态 / 小红书（短版）

```text
给我的陪伴 Bot 写了个“自我管理”插件。

现在可以直接私聊跟她说：
“把【傲娇怎么用】改成……先给我看改动”
她会先提案，我回“确认”才改；改前自动快照，能回滚。

不是让她乱改代码，是把人格/风格/白名单/TTS 变成可确认、可审计的工具调用。
AstrBot 插件，MIT，开源：https://github.com/SuHoKUO/astrbot_plugin_companion_admin
```

### X / Twitter

```text
Built a small AstrBot plugin: Companion Self-Admin.

Admins can DM the bot to edit its own persona sections, user styles, group allowlist, and TTS settings — with a propose → confirm → snapshot → rollback flow.

No code-level self-modification. MIT.
https://github.com/SuHoKUO/astrbot_plugin_companion_admin
```

---

## 6. 发布后

- [ ] 在 AstrBot 插件市场提交（如果支持 GitHub 链接）
- [ ] 把仓库 pin 到个人主页
- [ ] 在 README 顶部放一张实际聊天截图/GIF（可选，但很有用）
- [ ] 给 `v0.1.0` 打标签并上传 ZIP
- [ ] 检查 Release 的 ZIP 能直接安装
```
