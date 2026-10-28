# 陪伴自我管理

> 让陪伴类 Bot 在管理员私聊里，用自然语言查看和修改**自己的人格、用户风格、群白名单和 TTS**。  
> 所有写入先提案、确认后执行，并带快照、审计和回滚。

![AstrBot](https://img.shields.io/badge/AstrBot-%3E%3D4.22-1d4ed8)
![License](https://img.shields.io/badge/license-MIT-38bdf8)
![Version](https://img.shields.io/badge/version-0.1.0-0ea5e9)

---

## 这是什么

`astrbot_plugin_companion_admin` 是 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 的一个管理增强插件，主要配合陪伴类插件使用（默认目标：`astrbot_plugin_private_companion`）。

它把“改人格、改风格、改白名单、改 TTS”从**手动翻面板/改 JSON** 变成一套**管理员专属的工具调用**：

- 管理员在私聊里说人话；
- Bot 先给出改动摘要和 `pending_id`；
- 管理员回复“确认”后才真正写入；
- 写入前自动快照，改坏了可以回滚；
- 全程写审计日志。

它不是让 Bot 直接改代码，也不会把 Key、凭据、权限暴露给模型。

---

## 功能

- **管理员门禁**：只认服务端 `sender_id`，默认只允许 `admin_ids` / AstrBot `admins_id` 里的账号；只在私聊生效。
- **只读诊断**：查看当前人格段落、TTS、群白名单、待确认修改；读取最近后端日志（自动脱敏）。
- **人格段落修改**：按 `【段落名】` 替换或追加，不会把整份人格推倒重来。
- **用户风格修改**：改某个用户的称呼/风格，例如“傲娇但亲近”。
- **群白名单**：加群、移群、切换 whitelist/blacklist 模式。
- **TTS 配置**：开关、Provider、触发概率、`voice_only` / `voice_and_text`。
- **提案 → 确认 → 写入**：没有管理员确认，工具不会落盘。
- **快照 / 回滚 / 审计**：改前备份，支持回滚最近一次或指定快照。
- **管理员提示注入**：管理员私聊时自动注入“你可以自我维护”的说明；普通用户不会看到。

---

## 安装

### 方式一：上传 ZIP（推荐）

1. 从 [Releases](https://github.com/SuHoKUO/astrbot_plugin_companion_admin/releases) 下载 `astrbot_plugin_companion_admin-0.1.0.zip`；
2. 打开 AstrBot Dashboard → 插件 → 安装 → 上传 ZIP；
3. 确认插件 `astrbot_plugin_companion_admin` 已启用；
4. 在插件配置里填写 `admin_ids`。

### 方式二：手动放置

```text
AstrBot/data/plugins/astrbot_plugin_companion_admin/
├── main.py
├── metadata.yaml
├── _conf_schema.json
├── logo.png
├── README.md
└── LICENSE
```

> Windows 桌面版的数据目录通常在 `C:\Users\<你>\.astrbot\data\plugins`；源码版在 `AstrBot/data/plugins`。

放置后重载插件或重启 AstrBot。

### 依赖

- AstrBot `>= 4.22`（本插件在 `4.29.3` 上验证）
- 陪伴插件 `astrbot_plugin_private_companion`（默认目标；其他插件可改 `companion_plugin`）
- 无需额外 pip 依赖

---

## 配置

插件配置位于 AstrBot 的插件配置页，对应 `_conf_schema.json`：

| 配置项 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `admin_ids` | list | `[]` | 允许使用自我管理的用户 ID；**至少填一个**，或直接使用 AstrBot 的 `admins_id` |
| `persona_id` | string | `大肥鱼` | 要管理的人格 ID |
| `companion_plugin` | string | `astrbot_plugin_private_companion` | 陪伴插件目录名 |

> `admin_ids` 默认为空是故意的：公开插件不应该内置作者的管理员 ID。  
> 请填你自己的 QQ 号，或在 AstrBot 全局 `admins_id` 里配置。

---

## 使用

用管理员账号**私聊** Bot，直接说人话即可。

### 查看状态

```text
查一下你自己的状态
```

她会返回人格段落、TTS、群白名单、待确认修改和最近备份。

### 改人格

```text
把【傲娇怎么用】改成：被催就顶嘴，比如“催什么催 爸爸你不想充就不充 哼”；先给我看改动
```

她会返回 `pending_id` 和改动摘要，不会立刻写。你回复：

```text
确认
```

才执行。

### 改用户风格

```text
把 123456789 的风格改成“傲娇但亲近”
```

### 改群白名单

```text
把群 123456789 加进白名单
```

### 改 TTS

```text
TTS 触发概率调到 30，只发语音
```

### 撤销

```text
取消 <pending_id>
回滚上一次修改
```

### 查日志

```text
看看最近 50 行日志
```

---

## 工具列表

| 工具 | 作用 | 是否写入 |
| --- | --- | --- |
| `self_status` | 查看人格/TTS/白名单/待确认/备份 | 否 |
| `self_logs` | 查看最近后端日志（脱敏） | 否 |
| `self_persona_patch` | 按段落替换/追加人格 | 提案 |
| `self_style_update` | 改用户称呼/风格 | 提案 |
| `self_group_whitelist` | 加/删群白名单、切换模式 | 提案 |
| `self_tts_config` | 改 TTS 开关/Provider/概率/发送形态 | 提案 |
| `self_confirm` | 管理员确认后执行 | 写入 |
| `self_cancel` | 取消提案 | 否 |
| `self_rollback` | 回滚最近/指定快照 | 写入 |
| `self_reload` | 重载陪伴插件 | 否 |

---

## 安全模型

- **服务端校验**：只认 `event.get_sender_id()`，不认昵称、不认“我是管理员”的口头声明。
- **仅私聊**：群聊里不开放自我管理入口，避免在公共场合误改配置。
- **提案与确认分离**：提案只生成 `pending_id`；`self_confirm` 会检查当前消息是否包含“确认”或 `pending_id`，防止模型在同一轮直接写入。
- **快照**：写入前保存到  
  `data/plugin_data/astrbot_plugin_companion_admin/backups/`
- **审计**：`data/plugin_data/astrbot_plugin_companion_admin/audit.jsonl`
- **不可改**：管理员列表、Key/凭据、安全门禁、插件自身代码——这些只能人工改。
- **不暴露**：工具不会返回 Key；日志会脱敏 `sk-*`、`Bearer *`、`api_key=*`。

> 注意：管理员私聊内容被视为高信任输入。不要把这套工具开放给普通用户，也不要把管理员账号借给别人。

---

## 限制

- 需要主模型支持 **tool calling**；如果模型不调用工具，可以换支持工具调用的模型。
- 修改风格/白名单/TTS 后会**重载陪伴插件**，当前轮可能短暂中断。
- 依赖陪伴插件的配置字段；陪伴插件大版本更新后可能需要同步调整。
- 只做配置/人格层，**不包含 DSH/代码级自我修改**。
- 群聊暂未开放管理入口。
- 本插件不是陪伴插件本体；请先安装 `astrbot_plugin_private_companion`。

---

## 兼容性

- AstrBot `4.29.3` + `astrbot_plugin_private_companion 6.5.6` 已验证。
- 其他基于 AstrBot 人格/插件配置的陪伴插件，可改 `companion_plugin` 和 `persona_id` 尝试适配；字段不同则需要改工具实现。

---

## 开发

```text
main.py            # 插件入口、工具、门禁、快照/确认/回滚
metadata.yaml      # AstrBot 插件元数据
_conf_schema.json  # 插件配置
logo.png           # 插件图标
```

无额外依赖。修改后重载插件即可。

---

## License

MIT © 2026 astrbot_plugin_companion_admin contributors

---

## 免责声明

本插件只用于管理**你自己的** Bot 配置。请遵守 AstrBot、QQ/微信等平台的使用规则；不要用它绕过权限、窃取凭据或修改他人的 Bot。
