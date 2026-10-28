# Changelog

## 0.1.0 — 2026-10-29

首个版本。

### 新增

- 管理员门禁：只允许 `admin_ids` / AstrBot `admins_id`，仅私聊生效。
- 只读诊断：`self_status` 查看人格段落、TTS、群白名单、待确认修改和备份。
- 日志查看：`self_logs` 读取最近后端日志并脱敏。
- 人格段落修改：`self_persona_patch` 按 `【段落】` 替换/追加。
- 用户风格修改：`self_style_update` 修改称呼/风格。
- 群白名单：`self_group_whitelist` 加群/移群/切换模式。
- TTS 配置：`self_tts_config` 开关、Provider、触发概率、发送形态。
- 提案-确认：`self_confirm` / `self_cancel`；未确认不写入。
- 快照与回滚：`self_rollback`。
- 审计日志：`audit.jsonl`。
- 管理员提示注入：管理员私聊自动注入“可自我维护”的说明。

### 已知限制

- 需要主模型支持 tool calling。
- 修改风格/白名单/TTS 会重载陪伴插件，当前轮可能短暂中断。
- 仅私聊；不含代码级自我修改。
