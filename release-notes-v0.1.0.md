# v0.1.0 — 陪伴自我管理

首个版本。

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
