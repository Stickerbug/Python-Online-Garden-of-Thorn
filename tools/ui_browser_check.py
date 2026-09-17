# -*- coding: utf-8 -*-
"""浏览器实测 ``request_ui`` 的**客户端渲染层**（Round 78 / 批次 BX）。

静态检查（``tools/mod_atom_report.py``）只能证明"客户端源码里有对应分支"，
证明不了"真的渲染出来了"。这个脚本把**全部 20 种声明控件**过一遍引擎净化层，
再把净化后的组件丢进真浏览器里调 ``showV2UiRequest``，检查：

1. 每个控件都渲染出一个非空行（没有"分支缺失 -> 空行"）；
2. 文案是中文（标题 / 标签 / 文本 / 按钮）；
3. 点"确定"后发出的 ``v2_ui_response`` 载荷里每个互动控件都有值。

用法（需要先在本机起一个开发服，端口随意）::

    $env:PORT='5099'; python app.py          # 另开一个终端
    python tools/ui_browser_check.py --url http://127.0.0.1:5099/

依赖 ``npx``（``@playwright/cli``）与 ``playwright`` 浏览器；本脚本只做验证，
不写仓库里的长期文件（临时 JSON 放在 ``static/`` 下，结束时删除）。
"""

from __future__ import annotations

import argparse
import io
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import mod_loader  # noqa: E402
import mod_runtime_v2 as RT  # noqa: E402
import mod_spec_v2 as SPEC  # noqa: E402
from cards import CardInstance  # noqa: E402
from game_engine import EquipmentInstance, GameEngine  # noqa: E402

TEMP_NAME = "_codex_ui_harness.json"
TEMP_NAME_2 = "_codex_ui_harness_conditional.json"
TEMP_NAME_3 = "_codex_ui_harness_tabs.json"
TEMP_NAME_4 = "_codex_ui_harness_fields.json"
# 违禁词过滤实测用的样例（moderation.check_message_risk → 等级 3）：
# moderation="reject" 必须拒、="off" 必须放行、默认 "mask" 打码后放行。
RISKY_TEXT = "你这个傻逼"
TEXT_TYPES = ("text", "dynamic_text", "divider", "warning_text", "preview_value")
NUMBER_TYPES = ("slider", "number", "number_input")
CHOICE_TYPES = ("select", "radio_group", "multi_select", "card_catalog_picker")
PICKER_TYPES = ("card_picker", "multi_card_picker", "equipment_picker",
                "multi_equipment_picker", "player_picker", "target_picker")

EVAL_SCRIPT = (
    "async () => {"
    " const component = await (await fetch('/static/" + TEMP_NAME + "?ts=' + Date.now())).json();"
    " const captured = [];"
    " const originalEmit = window.emitModeEvent;"
    " window.emitModeEvent = (...args) => { captured.push(args); };"
    " const originalGuard = window.canSendGameAction;"
    " window.canSendGameAction = () => true;"
    " window.showV2UiRequest({ request_id: 'harness-1', component });"
    " const rows = [...document.querySelectorAll('#modal-content .v2-ui-control')].map(row => ({"
    "  cls: String(row.className || '').replace('v2-ui-control ', ''),"
    "  label: (row.querySelector('label.v2-ui-label') || {}).textContent || '',"
    "  text: (row.querySelector('.v2-ui-text') || {}).textContent || '',"
    "  children: row.children.length,"
    "  inputs: row.querySelectorAll('input').length,"
    "  selects: row.querySelectorAll('select').length,"
    "  pickers: row.querySelectorAll('.v2-ui-picker-option').length,"
    " }));"
    " const buttons = [...document.querySelectorAll('#modal-content .v2-ui-buttons button')];"
    " if (buttons[0]) buttons[0].click();"
    " window.emitModeEvent = originalEmit;"
    " window.canSendGameAction = originalGuard;"
    # 第二阶段：联动显隐 + 超时倒计时（带 timeout_ms 再开一次窗口）。
    " const conditional = await (await fetch('/static/" + TEMP_NAME_2 + "?ts=' + Date.now())).json();"
    " window.emitModeEvent = () => {};"
    " window.canSendGameAction = () => true;"
    " window.showV2UiRequest({ request_id: 'harness-2', component: conditional, timeout_ms: 5000 });"
    " const rows2 = [...document.querySelectorAll('#modal-content .v2-ui-control')];"
    " const extraRow = rows2[1];"
    " const lockedRow = rows2[2];"
    " const hiddenInitially = extraRow.style.display === 'none';"
    " const lockedDisabled = !!lockedRow.querySelector('input:disabled');"
    " const select = rows2[0].querySelector('select');"
    " if (select) { select.value = 'b'; select.dispatchEvent(new Event('change', { bubbles: true })); }"
    " const shownAfter = extraRow.style.display !== 'none';"
    " const timeoutText = (document.querySelector('#modal-content .v2-ui-timeout') || {}).textContent || '';"
    " for (const btn of [...document.querySelectorAll('#modal-content .v2-ui-buttons button')]) btn.click();"
    # 第三阶段：``tab`` 分页（切换条 + 默认页 + 点击切换）。
    " const tabbed = await (await fetch('/static/" + TEMP_NAME_3 + "?ts=' + Date.now())).json();"
    " window.emitModeEvent = () => {};"
    " window.canSendGameAction = () => true;"
    " window.showV2UiRequest({ request_id: 'harness-3', component: tabbed });"
    " const tabButtons = [...document.querySelectorAll('#modal-content .v2-ui-tabs .v2-ui-tab')];"
    " const panes = [...document.querySelectorAll('#modal-content .v2-ui-tab-pane')];"
    " const paneVisible = pane => !!(pane && pane.style.display !== 'none');"
    " const beforeSwitch = [paneVisible(panes[0]), paneVisible(panes[1])];"
    " if (tabButtons[1]) tabButtons[1].click();"
    " const afterSwitch = [paneVisible(panes[0]), paneVisible(panes[1])];"
    " for (const btn of [...document.querySelectorAll('#modal-content .v2-ui-buttons button')]) btn.click();"
    # 第四阶段：字段实测（输入记忆 / 文本输入属性 / 开关 / 多选默认值 / 违禁词载荷）。
    " const fields = await (await fetch('/static/" + TEMP_NAME_4 + "?ts=' + Date.now())).json();"
    " const captured4 = [];"
    " window.emitModeEvent = (...args) => { captured4.push(args); };"
    " window.canSendGameAction = () => true;"
    " window.showV2UiRequest({ request_id: 'harness-4', component: fields });"
    " const rows4 = [...document.querySelectorAll('#modal-content .v2-ui-control')];"
    " const memoSelect = rows4[0] ? rows4[0].querySelector('select') : null;"
    " const guardInput = rows4[1] ? rows4[1].querySelector('input') : null;"
    " const flagBox = rows4[2] ? rows4[2].querySelector('input') : null;"
    " const pickButtons = rows4[3] ? [...rows4[3].querySelectorAll('.v2-ui-picker-option')] : [];"
    " const numInput = rows4[4] ? rows4[4].querySelector('input') : null;"
    " const helpText = rows4[1] ? ((rows4[1].querySelector('.v2-ui-help') || {}).textContent || '') : '';"
    " const picksSelected = pickButtons.filter(b => b.classList.contains('selected')).map(b => b.dataset.value);"
    " if (guardInput) { guardInput.value = '" + RISKY_TEXT + "';"
    "  guardInput.dispatchEvent(new Event('input', { bubbles: true })); }"
    " const guardTyped = guardInput ? guardInput.value : '';"
    " for (const btn of [...document.querySelectorAll('#modal-content .v2-ui-buttons button')]) btn.click();"
    " const fieldPayloads = captured4.map(args => ({ event: args[0], kind: args[1], data: args[2] }));"
    " return JSON.stringify({ rowCount: rows.length, rows,"
    "  buttonTexts: buttons.map(b => b.textContent),"
    "  payloads: captured.map(args => ({ event: args[0], kind: args[1], data: args[2] })),"
    "  conditional: { hiddenInitially, shownAfter, lockedDisabled, timeoutText },"
    "  tabs: { buttons: tabButtons.map(b => b.textContent), beforeSwitch, afterSwitch },"
    "  fields: { memo: memoSelect ? memoSelect.value : null,"
    "   guardMaxLength: guardInput ? guardInput.maxLength : null,"
    "   guardPlaceholder: guardInput ? guardInput.placeholder : '',"
    "   guardValue: guardInput ? guardInput.value : '',"
    "   guardTyped, helpText, flagChecked: flagBox ? flagBox.checked : null,"
    "   picksSelected, numValue: numInput ? Number(numInput.value) : null,"
    "   payload: fieldPayloads.length ? fieldPayloads[0].data : null } });"
    " }"
)


def build_controls() -> list:
    controls = []
    for ctype in sorted(SPEC.VALID_UI_CONTROL_TYPES):
        control = {"id": f"c_{ctype}", "type": ctype,
                   "label_cn": f"标签{ctype}", "label_en": f"label {ctype}"}
        if ctype in TEXT_TYPES:
            control["text_cn"] = f"文本{ctype}"
            control["text_en"] = f"text {ctype}"
        if ctype in NUMBER_TYPES:
            control.update({"min": 0, "max": 5, "step": 1, "default": 2})
        if ctype in CHOICE_TYPES:
            control["options"] = [
                {"value": "a", "label_cn": "选项A", "label_en": "Option A"},
                {"value": "b", "label_cn": "选项B", "label_en": "Option B"},
            ]
        if ctype in PICKER_TYPES:
            control.update({"zones": ["hand"], "target": "source"})
        if ctype in ("dynamic_text", "preview_value"):
            control["value"] = {"op": "const", "value": 3}
            control["text_cn"] = f"文本{ctype} {{value}}"
        controls.append(control)
    return controls


def sanitized_component() -> dict:
    engine = GameEngine()
    engine.phase = "action"
    engine.current_player = 0
    engine.player_names = ["P1", "P2"]
    engine.players[0].hand = [CardInstance("Sewage"), CardInstance("Light")]
    engine.players[0].equipment = [EquipmentInstance(CardInstance("Disc"), owner=0)]
    context = {"source_player": 0, "target_player": 1, "vars": {}, "card": None}
    component = {
        "type": "modal",
        "title_cn": "控件渲染实测",
        "controls": build_controls(),
        "buttons": [
            {"id": "confirm", "role": "confirm", "text_cn": "确定", "text_en": "Confirm"},
            {"id": "cancel", "role": "cancel", "text_cn": "取消", "text_en": "Cancel"},
        ],
    }
    return RT._sanitize_ui_component(engine, context, component)


def conditional_component() -> dict:
    """第二阶段：联动显隐（``visible_when`` / ``disabled_when``）与超时倒计时。"""

    engine = GameEngine()
    engine.phase = "action"
    engine.current_player = 0
    engine.player_names = ["P1", "P2"]
    context = {"source_player": 0, "target_player": 1, "vars": {}, "card": None}
    component = {
        "type": "modal",
        "title_cn": "联动与超时测试",
        "controls": [
            {"id": "kind", "type": "select", "label_cn": "类型",
             "options": [{"value": "a", "label_cn": "甲"}, {"value": "b", "label_cn": "乙"}]},
            {"id": "extra", "type": "number_input", "label_cn": "只有乙才出现",
             "visible_if": {"control": "kind", "equals": "b"}},
            {"id": "locked", "type": "checkbox", "label_cn": "被禁用",
             "disabled_if": {"op": "compare", "a": {"op": "const", "value": 1},
                             "b": 1, "operator": "=="}},
        ],
        "buttons": [{"id": "confirm", "role": "confirm", "text_cn": "确定"}],
    }
    return RT._sanitize_ui_component(engine, context, component)


def tabbed_component() -> dict:
    """第三阶段：`tab` 参数驱动的控件分页。"""

    engine = GameEngine()
    engine.phase = "action"
    engine.current_player = 0
    engine.player_names = ["P1", "P2"]
    context = {"source_player": 0, "target_player": 1, "vars": {}, "card": None}
    component = {
        "type": "modal",
        "title_cn": "分页测试",
        "controls": [
            {"id": "a", "type": "number_input", "label_cn": "基础项",
             "tab": "basic", "tab_cn": "基础"},
            {"id": "b", "type": "select", "label_cn": "基础选项",
             "options": [{"value": "x", "label_cn": "X"}],
             "tab": "basic", "tab_cn": "基础"},
            {"id": "c", "type": "text_input", "label_cn": "高级项", "max_length": 8,
             "tab": "advanced", "tab_cn": "高级"},
            {"id": "d", "type": "checkbox", "label_cn": "高级开关",
             "tab": "advanced", "tab_cn": "高级"},
        ],
        "buttons": [{"id": "confirm", "role": "confirm", "text_cn": "确定"}],
    }
    return RT._sanitize_ui_component(engine, context, component)


def fields_component(moderation: str = "reject") -> tuple:
    """第四阶段：**字段实测**（返回 ``(净化后的组件, 引擎, 上下文)``）。

    覆盖四件事：

    * ``default_from``（输入记忆）：玩家 ``custom_vars`` 里的值要变成控件的默认值；
    * ``text_input`` 的属性：``max_length`` → maxlength、``placeholder_cn``、``default``、``help_text``；
    * ``checkbox`` / ``multi_select`` / ``number_input`` 的默认值；
    * 违禁词载荷：客户端把玩家输入的原文发出去，服务端按 ``moderation`` 策略收/拒。
    """

    engine = GameEngine()
    engine.phase = "action"
    engine.current_player = 0
    engine.player_names = ["P1", "P2"]
    engine.players[0].custom_vars = {"memo_value": "b"}
    context = {"source_player": 0, "target_player": 1, "vars": {}, "card": None}
    component = {
        "type": "modal",
        "title_cn": "字段实测",
        "controls": [
            {"id": "memo", "type": "select", "label_cn": "记忆选项",
             "options": [{"value": "a", "label_cn": "甲"}, {"value": "b", "label_cn": "乙"}],
             "default_from": {"player_var": "memo_value"}},
            {"id": "guard", "type": "text_input", "label_cn": "口令", "max_length": 8,
             "placeholder_cn": "输入口令", "default": "abc", "required": True,
             "help_text": "最多 8 个字", "moderation": moderation},
            {"id": "flag", "type": "checkbox", "label_cn": "开关", "default": True},
            {"id": "picks", "type": "multi_select", "label_cn": "多选",
             "options": [{"value": "a", "label_cn": "甲"}, {"value": "b", "label_cn": "乙"}],
             "min_select": 1, "max_select": 2, "default": ["a"]},
            {"id": "num", "type": "number_input", "label_cn": "数字",
             "min": 0, "max": 9, "step": 1, "default": 3},
        ],
        "buttons": [{"id": "confirm", "role": "confirm", "text_cn": "确定"}],
    }
    return RT._sanitize_ui_component(engine, context, component), engine, context


def moderation_check(values: dict, moderation: str) -> tuple:
    """把浏览器抓到的载荷丢回服务端响应校验（真链路的最后一环）。

    返回 ``(是否放行, 校验后的值)``：被拒时第二个元素是 ``None``。
    """

    component, engine, context = fields_component(moderation=moderation)
    try:
        normalized = RT.validate_v2_ui_response(
            engine, context, component, {"button": "confirm", "values": values})
    except RT.V2RuntimeError:
        return False, None
    return True, normalized


def run_browser(url: str, timeout: int) -> dict:
    static_dir = ROOT / "static"
    temp = static_dir / TEMP_NAME
    temp2 = static_dir / TEMP_NAME_2
    temp3 = static_dir / TEMP_NAME_3
    temp4 = static_dir / TEMP_NAME_4
    temp.write_text(json.dumps(sanitized_component(), ensure_ascii=False), encoding="utf-8")
    temp2.write_text(json.dumps(conditional_component(), ensure_ascii=False), encoding="utf-8")
    temp3.write_text(json.dumps(tabbed_component(), ensure_ascii=False), encoding="utf-8")
    temp4.write_text(json.dumps(fields_component()[0], ensure_ascii=False), encoding="utf-8")
    try:
        # Windows 上 npx 是 .cmd，必须经 cmd.exe 起（直接 CreateProcess 找不到）。
        npx = shutil.which("npx") or shutil.which("npx.cmd")
        if not npx:
            raise RuntimeError("找不到 npx；请先安装 Node.js/npm（playwright-cli 依赖它）")
        open_cmd = ["cmd", "/c", npx, "--yes", "--package", "@playwright/cli", "playwright-cli"]
        subprocess.run(open_cmd + ["open", url], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout, cwd=str(ROOT))
        result = subprocess.run(open_cmd + ["eval", EVAL_SCRIPT, "--raw"], capture_output=True,
                                text=True, encoding="utf-8", errors="replace",
                                timeout=timeout, cwd=str(ROOT))
        subprocess.run(open_cmd + ["close"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout, cwd=str(ROOT))
    finally:
        temp.unlink(missing_ok=True)
        temp2.unlink(missing_ok=True)
        temp3.unlink(missing_ok=True)
        temp4.unlink(missing_ok=True)
    payload = result.stdout.strip()
    if payload.startswith('"') and payload.endswith('"'):
        payload = json.loads(payload)
    return json.loads(payload)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="request_ui 客户端渲染实测")
    parser.add_argument("--url", default="http://127.0.0.1:5000/")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args(argv)

    mod_loader.merge_mod_cards_to_card_defs()
    data = run_browser(args.url, args.timeout)
    declared = sorted(SPEC.VALID_UI_CONTROL_TYPES)
    rows = data.get("rows") or []
    problems = []
    if len(rows) != len(declared):
        problems.append(f"渲染出的控件行数 {len(rows)} != 声明控件数 {len(declared)}")
    for row in rows:
        if not row.get("children"):
            problems.append(f"控件 {row.get('cls')} 渲染成空行（客户端缺分支？）")
        if not (row.get("label") or row.get("text")):
            problems.append(f"控件 {row.get('cls')} 没有渲染出任何中文文案")
        if row.get("cls") in ("v2-ui-control-text", "v2-ui-control-divider"):
            continue
    chinese_buttons = [text for text in data.get("buttonTexts") or [] if text.strip()]
    if chinese_buttons != ["确定", "取消"]:
        problems.append(f"按钮文案异常：{chinese_buttons}")
    payloads = data.get("payloads") or []
    values = (payloads[0]["data"].get("values") if payloads else {}) or {}
    interactive = [f"c_{name}" for name in declared
                   if name not in ("text", "dynamic_text", "divider", "warning_text", "preview_value")]
    missing = [cid for cid in interactive if cid not in values]
    if missing:
        problems.append(f"提交载荷里缺这些控件的值：{missing}")
    if payloads:
        print("提交载荷：", json.dumps(values, ensure_ascii=False))
    print(f"渲染控件行数：{len(rows)}（声明 {len(declared)}）｜按钮：{chinese_buttons}")
    conditional = data.get("conditional") or {}
    if conditional:
        print("联动/超时：", json.dumps(conditional, ensure_ascii=False))
        if not conditional.get("hiddenInitially"):
            problems.append("visible_when 联动：初始状态没有隐藏被控控件")
        if not conditional.get("shownAfter"):
            problems.append("visible_when 联动：把依赖控件切成命中值后仍然隐藏")
        if not conditional.get("lockedDisabled"):
            problems.append("disabled_if：被禁用的控件没有 disabled")
        if not str(conditional.get("timeoutText") or "").strip():
            problems.append("timeout_ms：没有渲染倒计时提示")
    tabs = data.get("tabs") or {}
    if tabs:
        print("分页：", json.dumps(tabs, ensure_ascii=False))
        if len(tabs.get("buttons") or []) != 2:
            problems.append(f"tab 分页：切换条按钮数应为 2，实际 {tabs.get('buttons')}")
        if tabs.get("beforeSwitch") != [True, False]:
            problems.append(f"tab 分页：默认页不对（{tabs.get('beforeSwitch')}）")
        if tabs.get("afterSwitch") != [False, True]:
            problems.append(f"tab 分页：切换后页状态不对（{tabs.get('afterSwitch')}）")
    # 第四阶段：字段实测 + 违禁词链路（浏览器抓载荷 → 服务端响应校验）。
    fields = data.get("fields") or {}
    if not fields:
        problems.append("字段实测阶段没有拿到数据（第四阶段脚本没跑？）")
    else:
        printed = dict(fields)
        printed["payload"] = (fields.get("payload") or {}).get("values")
        print("字段实测：", json.dumps(printed, ensure_ascii=False))
        if fields.get("memo") != "b":
            problems.append(f"default_from（输入记忆）没生效：select 默认值 {fields.get('memo')!r} != 'b'")
        if fields.get("guardMaxLength") != 8:
            problems.append(f"text_input 的 maxlength 没挂上：{fields.get('guardMaxLength')!r} != 8")
        if fields.get("guardPlaceholder") != "输入口令":
            problems.append(f"text_input 的 placeholder 没渲染：{fields.get('guardPlaceholder')!r}")
        if fields.get("guardValue") != RISKY_TEXT:
            problems.append(f"text_input 没有接受输入：{fields.get('guardValue')!r}")
        if fields.get("helpText") != "最多 8 个字":
            problems.append(f"help_text 没渲染：{fields.get('helpText')!r}")
        if fields.get("flagChecked") is not True:
            problems.append(f"checkbox 的默认值没勾上：{fields.get('flagChecked')!r}")
        if fields.get("picksSelected") != ["a"]:
            problems.append(f"multi_select 的默认选项没选上：{fields.get('picksSelected')!r}")
        if fields.get("numValue") != 3:
            problems.append(f"number_input 的默认值不对：{fields.get('numValue')!r}")
        values = ((fields.get("payload") or {}).get("values")) or {}
        if values.get("guard") != RISKY_TEXT:
            problems.append(f"提交载荷里的文本不是玩家输入的原文：{values.get('guard')!r}")
        if values.get("flag") is not True:
            problems.append(f"checkbox 载荷应是布尔 true，实际 {values.get('flag')!r}")
        if values.get("picks") != ["a"]:
            problems.append(f"multi_select 载荷应是 ['a']，实际 {values.get('picks')!r}")
        if values.get("num") != 3:
            problems.append(f"number_input 载荷应是 3，实际 {values.get('num')!r}")
        if values:
            rejected_ok, _ = moderation_check(values, "reject")
            off_ok, _ = moderation_check(values, "off")
            mask_ok, masked = moderation_check(values, "mask")
            if rejected_ok:
                problems.append("moderation=reject 没有拦住等级 3 的违禁词（服务端放行了）")
            if not off_ok:
                problems.append("moderation=off 误拦了文本（应当不过滤）")
            if not mask_ok:
                problems.append("moderation=mask 误拦了等级 3 的文本（应当打码放行）")
            elif masked and (masked.get("values") or {}).get("guard") == RISKY_TEXT:
                problems.append("moderation=mask 放行了原文，没有打码")
            print(f"违禁词链路：reject={'拦下' if not rejected_ok else '放行'} / "
                  f"off={'放行' if off_ok else '拦下'} / mask={'打码放行' if mask_ok else '拦下'}"
                  f"（掩码后 {((masked or {}).get('values') or {}).get('guard')!r}）")
    for problem in problems:
        print("  [失败]", problem)
    print("UI 浏览器实测：", "OK" if not problems else f"{len(problems)} 个问题")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
