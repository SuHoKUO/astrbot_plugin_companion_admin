"""陪伴自我管理 — 管理员通过自然语言查看/修改人格、风格、TTS、群白名单。

设计原则：
- 只有管理员（AstrBot admins_id + 本插件 admin_ids）在私聊里可以使用；
- 所有写操作先返回 diff/待确认 ID，管理员确认后才落盘；
- 落盘前保存快照，支持撤回；
- 不暴露 Key、凭据、系统路径；不允许修改权限/门禁本身。
"""

from __future__ import annotations

import asyncio
import copy
import json
import os
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import astrbot.api.star as star
from astrbot.api import llm_tool, logger
from astrbot.api.event import AstrMessageEvent, filter

try:
    from astrbot.core.utils.astrbot_path import (
        get_astrbot_data_path,
        get_astrbot_plugin_data_path,
    )
except Exception:  # pragma: no cover - 兼容旧版本
    def get_astrbot_data_path() -> str:
        return str(Path.home() / ".astrbot" / "data")

    def get_astrbot_plugin_data_path() -> str:
        return str(Path(get_astrbot_data_path()) / "plugin_data")

PLUGIN_NAME = "astrbot_plugin_companion_admin"
PENDING_TTL_SECONDS = 15 * 60


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class CompanionAdminPlugin(star.Star):
    def __init__(self, context: star.Context, config: Any = None) -> None:
        super().__init__(context)
        self.config = config if config is not None else {}
        self.data_dir = Path(star.StarTools.get_data_dir(PLUGIN_NAME))
        self.backup_dir = self.data_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.audit_path = self.data_dir / "audit.jsonl"
        self.pending: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # 基础工具
    # ------------------------------------------------------------------
    def _admin_ids(self) -> set[str]:
        ids: set[str] = set()
        try:
            core = self.context.get_config()
            ids.update(str(item) for item in (core.get("admins_id") or []))
        except Exception:
            pass
        try:
            ids.update(str(item) for item in (self.config.get("admin_ids") or []))
        except Exception:
            pass
        return {item for item in ids if item}

    def _guard(self, event: AstrMessageEvent) -> str:
        if not bool(getattr(event, "is_private_chat", lambda: True)()):
            return "自我管理只在私聊里可用。"
        sender = str(event.get_sender_id() or "").strip()
        if sender not in self._admin_ids():
            return "只有管理员可以使用自我管理。"
        return ""

    @property
    def companion_plugin(self) -> str:
        try:
            return str(self.config.get("companion_plugin") or "astrbot_plugin_private_companion")
        except Exception:
            return "astrbot_plugin_private_companion"

    @property
    def persona_id(self) -> str:
        try:
            return str(self.config.get("persona_id") or "大肥鱼")
        except Exception:
            return "大肥鱼"

    def _companion_config_path(self) -> Path:
        return self._data_root() / "config" / f"{self.companion_plugin}_config.json"

    def _companions_path(self) -> Path:
        return self._data_root() / "plugin_data" / self.companion_plugin / "companions.json"

    @staticmethod
    def _data_root() -> Path:
        root = Path(get_astrbot_data_path())
        if not (root / "config").exists():
            fallback = Path.home() / ".astrbot" / "data"
            if (fallback / "config").exists():
                return fallback
        return root

    @staticmethod
    def _read_json(path: Path, default: Any) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return default

    @staticmethod
    def _write_json(path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)

    async def _reload_companion(self) -> str:
        manager = getattr(self.context, "_star_manager", None)
        if manager is None or not hasattr(manager, "reload"):
            return "未找到插件管理器，请手动重载陪伴插件。"
        try:
            result = manager.reload(self.companion_plugin)
            if asyncio.iscoroutine(result):
                result = await result
            return "已重载陪伴插件。"
        except Exception as exc:
            return f"重载失败：{type(exc).__name__}"

    async def _persona_prompt(self) -> str:
        pm = getattr(self.context, "persona_manager", None)
        if pm is None:
            raise RuntimeError("persona_manager 不可用")
        persona = await pm.get_persona(self.persona_id)
        if isinstance(persona, dict):
            return str(persona.get("system_prompt") or persona.get("prompt") or "")
        return str(
            getattr(persona, "system_prompt", None)
            or getattr(persona, "prompt", None)
            or ""
        )

    async def _update_persona(self, prompt: str) -> str:
        pm = getattr(self.context, "persona_manager", None)
        if pm is None:
            return "persona_manager 不可用"
        await pm.update_persona(self.persona_id, system_prompt=prompt)
        return "人格已更新。"

    # ------------------------------------------------------------------
    # 待确认修改 / 快照 / 审计
    # ------------------------------------------------------------------
    def _cleanup_pending(self) -> None:
        now = time.time()
        for key in list(self.pending):
            if now - float(self.pending[key].get("created", 0)) > PENDING_TTL_SECONDS:
                self.pending.pop(key, None)

    def _snapshot(self, kind: str, before: Any, label: str = "", path: str = "") -> str:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        name = f"{stamp}-{kind}-{uuid.uuid4().hex[:6]}.json"
        target = self.backup_dir / name
        self._write_json(
            target,
            {
                "created_at": _now_text(),
                "kind": kind,
                "label": label,
                "path": path,
                "before": before,
            },
        )
        return name

    def _audit(self, event: AstrMessageEvent, action: str, detail: Any) -> None:
        record = {
            "at": _now_text(),
            "sender": str(event.get_sender_id() or ""),
            "action": action,
            "detail": detail,
        }
        try:
            with self.audit_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def _propose(
        self,
        event: AstrMessageEvent,
        *,
        kind: str,
        summary: str,
        payload: dict[str, Any],
        backup: str,
    ) -> str:
        self._cleanup_pending()
        pending_id = uuid.uuid4().hex[:8]
        self.pending[pending_id] = {
            "kind": kind,
            "summary": summary,
            "payload": payload,
            "backup": backup,
            "sender": str(event.get_sender_id() or ""),
            "created": time.time(),
        }
        self._audit(event, f"propose:{kind}", {"pending_id": pending_id, "summary": summary})
        return json.dumps(
            {
                "ok": True,
                "pending_id": pending_id,
                "summary": summary,
                "instruction": "把 summary 用自然语言发给管理员，等管理员确认后再调用 self_confirm(pending_id)。不要直接说已经改好。",
            },
            ensure_ascii=False,
        )

    async def _apply_pending(self, pending_id: str) -> str:
        item = self.pending.pop(pending_id, None)
        if item is None:
            return "没有找到这个待确认修改（可能已过期）。"
        kind = item["kind"]
        payload = item["payload"]
        if kind == "persona":
            result = await self._update_persona(str(payload["after"]))
        elif kind == "companions":
            self._write_json(self._companions_path(), payload["after"])
            result = await self._reload_companion()
        elif kind == "companion_config":
            self._write_json(self._companion_config_path(), payload["after"])
            result = await self._reload_companion()
        elif kind == "tts":
            self._write_json(self._companion_config_path(), payload["companion_after"])
            try:
                core = self.context.get_config()
                core["provider_tts_settings"] = payload["core_after"]
                core.save_config()
            except Exception as exc:
                result = f"陪伴 TTS 已写入，但核心 TTS 配置保存失败：{type(exc).__name__}"
                return result
            result = await self._reload_companion()
        else:
            result = "未知修改类型。"
        return result

    # ------------------------------------------------------------------
    # 管理员自我维护模式提示
    # ------------------------------------------------------------------
    @filter.on_llm_request(priority=-50)
    async def on_llm_request(self, event: AstrMessageEvent, req: Any) -> None:
        """管理员私聊时，把“可以自我维护”的说明注入本轮提示词。"""
        if self._guard(event):
            return
        section = (
            "【自我管理】\n"
            "你是管理员，拥有 self_* 工具，可以查看和修改自己的人格、用户风格、群白名单、TTS。\n"
            "只有当管理员明确要求“改你自己/改人格/改配置”时才使用这些工具；普通聊天不要调用。\n"
            "任何写入都必须先提案，把 pending_id 和改动摘要发给管理员，等管理员确认后再调用 self_confirm；"
            "不要直接说已经改好。不要修改管理员列表、凭据、安全门禁或本插件自身。\n"
        )
        try:
            current = str(getattr(req, "system_prompt", "") or "")
            if "【自我管理】" not in current:
                req.system_prompt = f"{current}\n\n{section}" if current else section
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 工具：只读
    # ------------------------------------------------------------------
    @llm_tool(name="self_status")
    async def self_status(self, event: AstrMessageEvent) -> str:
        """查看自己的当前人格长度、TTS、群白名单、管理员和待确认修改。仅管理员可用。"""
        denied = self._guard(event)
        if denied:
            return denied
        prompt = ""
        try:
            prompt = await self._persona_prompt()
        except Exception:
            pass
        companion = self._read_json(self._companion_config_path(), {})
        core = {}
        try:
            core = dict(self.context.get_config().get("provider_tts_settings") or {})
        except Exception:
            pass
        return json.dumps(
            {
                "ok": True,
                "persona_id": self.persona_id,
                "persona_chars": len(prompt),
                "persona_sections": [
                    line.strip()
                    for line in prompt.splitlines()
                    if line.strip().startswith("【") and line.strip().endswith("】")
                ],
                "admins_count": len(self._admin_ids()),
                "tts_core": {
                    "enable": core.get("enable"),
                    "provider_id": core.get("provider_id"),
                    "trigger_probability": core.get("trigger_probability"),
                },
                "tts_companion": {
                    "enable_tts_enhancement": companion.get("enable_tts_enhancement"),
                    "tts_trigger_probability": companion.get("tts_trigger_probability"),
                    "tts_delivery_mode": companion.get("tts_delivery_mode"),
                    "tts_provider_id_zh": companion.get("tts_provider_id_zh"),
                },
                "group_access_mode": companion.get("group_access_mode"),
                "group_whitelist_ids": companion.get("group_whitelist_ids"),
                "pending": [
                    {"id": key, "summary": value.get("summary"), "kind": value.get("kind")}
                    for key, value in self.pending.items()
                ],
                "backups": sorted(
                    item.name for item in self.backup_dir.glob("*.json")
                )[-10:],
            },
            ensure_ascii=False,
        )

    @llm_tool(name="self_logs")
    async def self_logs(self, event: AstrMessageEvent, lines: str = "30") -> str:
        """查看最近的后端日志（脱敏），用于排查没声音、没图、没回复等问题。仅管理员可用。

        Args:
            lines(string): 返回最后多少行，1-100，默认 30。
        """
        denied = self._guard(event)
        if denied:
            return denied
        try:
            count = max(1, min(100, int(str(lines or "30").strip())))
        except ValueError:
            count = 30
        path = self._data_root() / "logs" / "backend.log"
        try:
            raw = path.read_text(encoding="utf-8", errors="replace").splitlines()[-count:]
        except Exception as exc:
            return f"读取日志失败：{type(exc).__name__}"
        text = "\n".join(raw)
        text = re.sub(r"sk-[A-Za-z0-9_\-]{6,}", "sk-***", text)
        text = re.sub(r"(?i)bearer\s+[A-Za-z0-9._\-]+", "Bearer ***", text)
        text = re.sub(r"(?i)(api[_-]?key[\"']?\s*[:=]\s*)[\"']?[^\s\"']+", r"\1***", text)
        return text[-12000:]

    # ------------------------------------------------------------------
    # 工具：人格
    # ------------------------------------------------------------------
    @llm_tool(name="self_persona_patch")
    async def self_persona_patch(
        self,
        event: AstrMessageEvent,
        section: str,
        content: str,
        mode: str = "replace",
    ) -> str:
        """提案修改自己人格中的某个【段落】。不会立即写入，需要 self_confirm。

        Args:
            section(string): 段落名，不含【】，例如“傲娇怎么用”“日程与状态”。
            content(string): 新的段落正文；mode=append 时追加到原段落末尾。
            mode(string): replace 或 append，默认 replace。
        """
        denied = self._guard(event)
        if denied:
            return denied
        section = str(section or "").strip().strip("【】")
        content = str(content or "").strip()
        mode = str(mode or "replace").strip().lower()
        if not section or not content:
            return "section 和 content 都不能为空。"
        if mode not in {"replace", "append"}:
            return "mode 只能是 replace 或 append。"
        try:
            before = await self._persona_prompt()
        except Exception as exc:
            return f"读取人格失败：{type(exc).__name__}"
        after = self._patch_section(before, section, content, mode)
        if after == before:
            return "内容没有变化。"
        backup = self._snapshot("persona", before, label=f"persona:{section}")
        summary = f"修改人格段落【{section}】\n修改前：{before[:80]}...\n修改后：{after[:80]}..."
        return self._propose(
            event,
            kind="persona",
            summary=summary,
            payload={"after": after, "section": section, "mode": mode},
            backup=backup,
        )

    @staticmethod
    def _patch_section(prompt: str, section: str, content: str, mode: str) -> str:
        header = f"【{section}】"
        start = prompt.find(header)
        if start < 0:
            return prompt.rstrip() + f"\n\n{header}\n{content.strip()}"
        body_start = start + len(header)
        next_start = prompt.find("\n【", body_start)
        existing = prompt[body_start: next_start if next_start >= 0 else len(prompt)].strip()
        new_body = existing if mode == "append" else ""
        if new_body:
            new_body = f"{new_body}\n{content.strip()}"
        else:
            new_body = content.strip()
        tail = prompt[next_start:] if next_start >= 0 else ""
        return prompt[:start] + header + "\n" + new_body + ("\n\n" + tail.lstrip("\n") if tail else "")

    # ------------------------------------------------------------------
    # 工具：用户风格
    # ------------------------------------------------------------------
    @llm_tool(name="self_style_update")
    async def self_style_update(
        self,
        event: AstrMessageEvent,
        user_id: str,
        style: str = "",
        nickname: str = "",
    ) -> str:
        """提案修改某个用户的称呼/风格（如把某个用户的风格改成“傲娇但亲近”）。需要 self_confirm。

        Args:
            user_id(string): 用户 ID，例如 123456789。
            style(string): 新风格；留空表示不改。
            nickname(string): 新称呼；留空表示不改。
        """
        denied = self._guard(event)
        if denied:
            return denied
        user_id = str(user_id or "").strip()
        style = str(style or "").strip()
        nickname = str(nickname or "").strip()
        if not user_id or (not style and not nickname):
            return "user_id 必填，style 和 nickname 至少填一个。"
        path = self._companions_path()
        data = self._read_json(path, None)
        if not isinstance(data, dict):
            return "读取 companions.json 失败。"
        users = data.get("users")
        if not isinstance(users, dict):
            return "companions.json 里没有 users。"
        user = users.get(user_id)
        if not isinstance(user, dict):
            return f"没有找到用户 {user_id}。"
        before_text = json.dumps(data, ensure_ascii=False)
        after = copy.deepcopy(data)
        after_user = after["users"][user_id]
        if style:
            after_user["style"] = style[:24]
        if nickname:
            after_user["nickname"] = nickname[:24]
        backup = self._snapshot("companions", before_text, label=f"style:{user_id}", path=str(path))
        summary = f"修改用户 {user_id}：style={style or '不变'}，nickname={nickname or '不变'}"
        return self._propose(
            event,
            kind="companions",
            summary=summary,
            payload={"after": after},
            backup=backup,
        )

    # ------------------------------------------------------------------
    # 工具：群白名单
    # ------------------------------------------------------------------
    @llm_tool(name="self_group_whitelist")
    async def self_group_whitelist(
        self,
        event: AstrMessageEvent,
        add: str = "",
        remove: str = "",
        mode: str = "",
    ) -> str:
        """提案修改群白名单/黑名单模式。需要 self_confirm。

        Args:
            add(string): 要加入白名单的群号，逗号或空格分隔。
            remove(string): 要移出白名单的群号，逗号或空格分隔。
            mode(string): whitelist 或 blacklist；留空不改。
        """
        denied = self._guard(event)
        if denied:
            return denied
        path = self._companion_config_path()
        data = self._read_json(path, None)
        if not isinstance(data, dict):
            return "读取陪伴配置失败。"
        mode = str(mode or "").strip().lower()
        if mode and mode not in {"whitelist", "blacklist"}:
            return "mode 只能是 whitelist 或 blacklist。"
        add_ids = [item for item in str(add or "").replace("，", ",").replace(" ", ",").split(",") if item.strip()]
        remove_ids = [item for item in str(remove or "").replace("，", ",").replace(" ", ",").split(",") if item.strip()]
        if not add_ids and not remove_ids and not mode:
            return "至少提供 add、remove 或 mode 之一。"

        def update(obj: Any) -> int:
            changed = 0
            if isinstance(obj, dict):
                if "group_whitelist_ids" in obj:
                    current = [str(item) for item in (obj.get("group_whitelist_ids") or [])]
                    for item in add_ids:
                        if item not in current:
                            current.append(item)
                    for item in remove_ids:
                        current = [value for value in current if value != item]
                    obj["group_whitelist_ids"] = current
                    changed += 1
                if mode and "group_access_mode" in obj:
                    obj["group_access_mode"] = mode
                    changed += 1
                for value in obj.values():
                    if isinstance(value, dict):
                        changed += update(value)
            return changed

        after = copy.deepcopy(data)
        changed = update(after)
        if not changed:
            return "没有找到可修改的白名单字段。"
        backup = self._snapshot("companion_config", data, label="group_whitelist", path=str(path))
        summary = f"群名单变更：加入 {add_ids}，移出 {remove_ids}，模式 {mode or '不变'}"
        return self._propose(
            event,
            kind="companion_config",
            summary=summary,
            payload={"after": after},
            backup=backup,
        )

    # ------------------------------------------------------------------
    # 工具：TTS
    # ------------------------------------------------------------------
    @llm_tool(name="self_tts_config")
    async def self_tts_config(
        self,
        event: AstrMessageEvent,
        enabled: str = "",
        provider_id: str = "",
        trigger_probability: str = "",
        delivery_mode: str = "",
    ) -> str:
        """提案修改 TTS 开关、Provider、触发概率和发送形态。需要 self_confirm。

        Args:
            enabled(string): true/false；留空不改。
            provider_id(string): AstrBot TTS Provider ID，例如 edge_tts；留空不改。
            trigger_probability(string): 0-100 的整数；留空不改。
            delivery_mode(string): voice_only 或 voice_and_text；留空不改。
        """
        denied = self._guard(event)
        if denied:
            return denied
        path = self._companion_config_path()
        data = self._read_json(path, None)
        if not isinstance(data, dict):
            return "读取陪伴配置失败。"
        enabled_text = str(enabled or "").strip().lower()
        enabled_bool = None
        if enabled_text:
            if enabled_text not in {"true", "false", "1", "0", "on", "off"}:
                return "enabled 只能是 true/false。"
            enabled_bool = enabled_text in {"true", "1", "on"}
        try:
            probability = int(trigger_probability) if str(trigger_probability or "").strip() else None
        except ValueError:
            return "trigger_probability 必须是 0-100 的整数。"
        if probability is not None and not 0 <= probability <= 100:
            return "trigger_probability 必须在 0-100 之间。"
        provider_id = str(provider_id or "").strip()
        delivery_mode = str(delivery_mode or "").strip().lower()
        if delivery_mode and delivery_mode not in {"voice_only", "voice_and_text"}:
            return "delivery_mode 只能是 voice_only 或 voice_and_text。"
        if enabled_bool is None and not provider_id and probability is None and not delivery_mode:
            return "至少提供 enabled、provider_id、trigger_probability 或 delivery_mode 之一。"

        def update(obj: Any) -> int:
            changed = 0
            if isinstance(obj, dict):
                if enabled_bool is not None and "enable_tts_enhancement" in obj:
                    obj["enable_tts_enhancement"] = enabled_bool
                    changed += 1
                if probability is not None and "tts_trigger_probability" in obj:
                    obj["tts_trigger_probability"] = probability
                    changed += 1
                if provider_id and "tts_provider_id_zh" in obj:
                    obj["tts_provider_id_zh"] = provider_id
                    changed += 1
                if delivery_mode and "tts_delivery_mode" in obj:
                    obj["tts_delivery_mode"] = delivery_mode
                    changed += 1
                for value in obj.values():
                    if isinstance(value, dict):
                        changed += update(value)
            return changed

        after = copy.deepcopy(data)
        changed = update(after)
        if not changed:
            return "没有找到可修改的 TTS 字段。"

        core_before: dict[str, Any] = {}
        try:
            core_before = copy.deepcopy(dict(self.context.get_config().get("provider_tts_settings") or {}))
        except Exception:
            pass
        core_after = copy.deepcopy(core_before)
        if enabled_bool is not None:
            core_after["enable"] = enabled_bool
        if provider_id:
            core_after["provider_id"] = provider_id
            core_after["enable"] = True
        if probability is not None:
            core_after["trigger_probability"] = 0.0
        backup = self._snapshot(
            "tts",
            {"companion": data, "core": core_before},
            label="tts",
            path=str(path),
        )
        summary = (
            f"TTS 修改：enable={enabled_bool if enabled_bool is not None else '不变'}，"
            f"provider={provider_id or '不变'}，概率={probability if probability is not None else '不变'}，"
            f"发送形态={delivery_mode or '不变'}"
        )
        return self._propose(
            event,
            kind="tts",
            summary=summary,
            payload={"companion_after": after, "core_after": core_after},
            backup=backup,
        )

    # ------------------------------------------------------------------
    # 工具：确认 / 取消 / 回滚
    # ------------------------------------------------------------------
    @llm_tool(name="self_confirm")
    async def self_confirm(self, event: AstrMessageEvent, pending_id: str) -> str:
        """管理员确认后，执行之前 self_persona_patch / self_style_update / self_group_whitelist 的修改。

        Args:
            pending_id(string): 提案返回的 pending_id。
        """
        denied = self._guard(event)
        if denied:
            return denied
        item = self.pending.get(str(pending_id or "").strip())
        if item is None:
            return "没有找到这个待确认修改（可能已过期）。"
        if item.get("sender") != str(event.get_sender_id() or ""):
            return "这个修改不是当前管理员发起的。"
        raw_text = str(getattr(event, "message_str", "") or "")
        if "确认" not in raw_text and str(pending_id) not in raw_text:
            return "还没有收到管理员的确认。请先把改动发给管理员，等管理员回复「确认」后再调用 self_confirm；不要在提案的同一轮直接写入。"
        result = await self._apply_pending(str(pending_id))
        self._audit(event, "confirm", {"pending_id": pending_id, "result": result})
        return result

    @llm_tool(name="self_cancel")
    async def self_cancel(self, event: AstrMessageEvent, pending_id: str) -> str:
        """取消一个待确认修改。

        Args:
            pending_id(string): 提案返回的 pending_id。
        """
        denied = self._guard(event)
        if denied:
            return denied
        item = self.pending.pop(str(pending_id or "").strip(), None)
        if item is None:
            return "没有找到这个待确认修改。"
        self._audit(event, "cancel", {"pending_id": pending_id})
        return "已取消，没有写入。"

    @llm_tool(name="self_rollback")
    async def self_rollback(self, event: AstrMessageEvent, backup_id: str = "") -> str:
        """用最近一次（或指定）快照回滚人格/配置。仅管理员可用。

        Args:
            backup_id(string): 快照文件名；留空使用最近一次。
        """
        denied = self._guard(event)
        if denied:
            return denied
        backup_id = str(backup_id or "").strip()
        if backup_id:
            target = self.backup_dir / backup_id
        else:
            files = sorted(self.backup_dir.glob("*.json"))
            target = files[-1] if files else None
        if target is None or not target.exists():
            return "没有可用快照。"
        data = self._read_json(target, None)
        if not isinstance(data, dict):
            return "快照文件无效。"
        kind = data.get("kind")
        before = data.get("before")
        if kind == "persona":
            result = await self._update_persona(str(before))
        elif kind == "companions":
            self._write_json(self._companions_path(), json.loads(str(before)))
            result = await self._reload_companion()
        elif kind == "companion_config":
            value = before if isinstance(before, dict) else json.loads(str(before))
            self._write_json(self._companion_config_path(), value)
            result = await self._reload_companion()
        elif kind == "tts":
            payload_before = json.loads(str(before)) if isinstance(before, str) else before
            if isinstance(payload_before, dict):
                companion_before = payload_before.get("companion")
                core_before = payload_before.get("core")
                if isinstance(companion_before, dict):
                    self._write_json(self._companion_config_path(), companion_before)
                if isinstance(core_before, dict):
                    try:
                        core = self.context.get_config()
                        core["provider_tts_settings"] = core_before
                        core.save_config()
                    except Exception:
                        pass
            result = await self._reload_companion()
        else:
            result = "该快照类型暂不支持自动回滚。"
        self._audit(event, "rollback", {"backup": target.name, "result": result})
        return f"已回滚 {target.name}。{result}"

    @llm_tool(name="self_reload")
    async def self_reload(self, event: AstrMessageEvent) -> str:
        """重载陪伴插件，让配置类修改生效。仅管理员可用。"""
        denied = self._guard(event)
        if denied:
            return denied
        return await self._reload_companion()
