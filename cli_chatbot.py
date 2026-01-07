"""Interactive CLI chatbot with streaming node output."""

from __future__ import annotations

import curses
import datetime as dt
import json
import os
import queue
import threading
import time
from typing import Dict, List, Optional, Tuple

from agent.deps import COMMON_PREREQS, DEPS
from agent.orchestrator import run_turn
from agent.storage.conversation_store import append_event
from agent.storage.paths import session_paths, user_dir
from agent.storage.profile_store import load_profile, save_profile
from agent.ui.state import ChatState, apply_event


def _list_users(root: str) -> List[str]:
    if not os.path.exists(root):
        return []
    users = []
    for name in sorted(os.listdir(root)):
        profile_path = os.path.join(root, name, "profile.json")
        if os.path.exists(profile_path):
            users.append(name)
    return users


def _input_int(prompt: str, default: Optional[int] = None) -> int:
    while True:
        raw = input(f"{prompt} [{default}]: " if default is not None else f"{prompt}: ").strip()
        if not raw and default is not None:
            return default
        try:
            return int(raw)
        except ValueError:
            print("请输入数字。")


def _input_choice(prompt: str, choices: List[str], default: Optional[str] = None) -> str:
    choice_set = {c.lower() for c in choices}
    while True:
        raw = input(f"{prompt} ({'/'.join(choices)}) [{default}]: ").strip().lower()
        if not raw and default is not None:
            return default
        if raw in choice_set:
            return raw
        print("请选择有效选项。")


def _create_profile(user_id: str) -> Tuple[str, Dict]:
    print("创建新用户 profile：")
    year = _input_int("出生年", 1990)
    month = _input_int("出生月", 1)
    day = _input_int("出生日", 1)
    hour = _input_int("出生时", 8)
    minute = _input_int("出生分", 0)
    second = _input_int("出生秒", 0)
    gender = _input_choice("性别", ["male", "female"], "male")
    time_unknown = _input_choice("是否未知出生时辰", ["yes", "no"], "no") == "yes"
    profile = {
        "user_id": user_id,
        "birth": {
            "year": year,
            "month": month,
            "day": day,
            "hour": hour,
            "minute": minute,
            "second": second,
        },
        "gender": gender,
        "birth_time_unknown": time_unknown,
        "prompt_config": "lingyun_cat",
        "node_cache": {},
    }
    profile_path, _ = session_paths(user_id, session_id="init")
    save_profile(profile_path, profile)
    return profile_path, profile


def _select_user() -> Tuple[str, Dict, str]:
    root = os.path.join(os.path.dirname(__file__), "storage", "users")
    users = _list_users(root)
    if users:
        print("已有用户：")
        for idx, uid in enumerate(users, start=1):
            print(f"{idx}) {uid}")
        print("n) 新建用户")
        raw = input("请选择用户: ").strip().lower()
        if raw == "n":
            user_id = input("输入新 user_id: ").strip()
            profile_path, profile = _create_profile(user_id)
            return user_id, profile, profile_path
        if raw.isdigit() and 1 <= int(raw) <= len(users):
            user_id = users[int(raw) - 1]
            profile_path = os.path.join(root, user_id, "profile.json")
            return user_id, load_profile(profile_path), profile_path
    user_id = input("输入新 user_id: ").strip()
    profile_path, profile = _create_profile(user_id)
    return user_id, profile, profile_path


def _select_conversation(user_id: str) -> str:
    base = os.path.join(user_dir(user_id), "conversations")
    os.makedirs(base, exist_ok=True)
    sessions = sorted([p for p in os.listdir(base) if p.endswith(".jsonl")])
    if sessions:
        print("已有会话：")
        for idx, name in enumerate(sessions, start=1):
            print(f"{idx}) {name}")
        print("n) 新会话")
        raw = input("请选择会话: ").strip().lower()
        if raw == "n":
            _, convo_path = session_paths(user_id)
            return convo_path
        if raw.isdigit() and 1 <= int(raw) <= len(sessions):
            return os.path.join(base, sessions[int(raw) - 1])
    _, convo_path = session_paths(user_id)
    return convo_path


def _load_history(convo_path: str) -> List[Dict[str, str]]:
    if not os.path.exists(convo_path):
        return []
    messages: List[Dict[str, str]] = []
    with open(convo_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "user_message":
                messages.append({"role": "user", "text": event.get("text", "")})
            elif event.get("type") == "assistant_final":
                messages.append({"role": "assistant", "text": event.get("text", "")})
    return messages


def _node_order() -> List[str]:
    nodes = ["PLANNER"] + list(COMMON_PREREQS)
    for node in DEPS.keys():
        if node not in nodes:
            nodes.append(node)
    if "TIME_CONTEXT" not in nodes:
        nodes.append("TIME_CONTEXT")
    if "FINAL" not in nodes:
        nodes.append("FINAL")
    return nodes


def _wrap_text(text: str, width: int) -> List[str]:
    if width <= 0:
        return []
    lines: List[str] = []
    for paragraph in text.splitlines() or [""]:
        line = paragraph
        while len(line) > width:
            lines.append(line[:width])
            line = line[width:]
        lines.append(line)
    return lines


def _safe_addnstr(stdscr, y: int, x: int, text: str, width: int) -> None:
    h, w = stdscr.getmaxyx()
    if y < 0 or y >= h or x < 0 or x >= w:
        return
    max_width = min(width, w - x)
    if max_width <= 0:
        return
    try:
        stdscr.addnstr(y, x, (text or "")[:max_width], max_width)
    except curses.error:
        return


def _render_nodes_view(stdscr, state: ChatState, start_y: int, height: int, width: int) -> None:
    left_w = max(24, min(40, width // 3))
    right_w = max(20, width - left_w - 1)
    node_lines = []
    for idx, node in enumerate(state.node_order):
        node_state = state.nodes.get(node)
        status = node_state.status if node_state else "idle"
        expanded = "+" if node_state and node_state.expanded else "-"
        prefix = ">" if idx == state.selected_index else " "
        node_lines.append(f"{prefix}[{expanded}] {node} ({status})")
    for i in range(height):
        if i < len(node_lines):
            _safe_addnstr(stdscr, start_y + i, 0, node_lines[i].ljust(left_w), left_w)
        else:
            _safe_addnstr(stdscr, start_y + i, 0, " " * left_w, left_w)
    selected = state.node_order[state.selected_index]
    output = state.nodes[selected].output if state.nodes[selected].expanded else "[collapsed] 按 SPACE 展开"
    output_lines = _wrap_text(output, right_w)
    for i in range(height):
        text = output_lines[-height + i] if i >= height - len(output_lines) else ""
        _safe_addnstr(stdscr, start_y + i, left_w + 1, text.ljust(right_w), right_w)


def _render_chat_view(stdscr, state: ChatState, start_y: int, height: int, width: int) -> None:
    lines: List[str] = []
    for msg in state.messages:
        role = "You" if msg["role"] == "user" else "Assistant"
        lines.extend(_wrap_text(f"{role}: {msg['text']}", width))
        lines.append("")
    lines = [ln for ln in lines if ln is not None]
    lines = lines[-height:] if len(lines) > height else lines
    for i in range(height):
        text = lines[i] if i < len(lines) else ""
        _safe_addnstr(stdscr, start_y + i, 0, text.ljust(width), width)


def _run_chat_ui(
    stdscr,
    profile: Dict,
    profile_path: str,
    convo_path: str,
    user_id: str,
) -> None:
    stdscr.nodelay(True)
    stdscr.keypad(True)
    curses.curs_set(0)

    state = ChatState(node_order=_node_order())
    for node, entry in profile.get("node_cache", {}).items():
        if node in state.nodes:
            state.nodes[node].status = "cache"
            state.nodes[node].output = state.nodes[node].output or ""
            apply_event(state, {"type": "node_end", "node": node, "output": entry.get("output"), "cached": True})

    for msg in _load_history(convo_path):
        state.messages.append(msg)

    event_q: queue.Queue = queue.Queue()

    def sink(event: Dict) -> None:
        event_q.put(event)

    input_buffer = ""
    running_thread: Optional[threading.Thread] = None

    while True:
        try:
            while True:
                event = event_q.get_nowait()
                apply_event(state, event)
        except queue.Empty:
            pass

        h, w = stdscr.getmaxyx()
        stdscr.erase()
        header = f"user={user_id} session={os.path.basename(convo_path)} mode={state.view_mode}  (Tab切换, ↑↓选择, Space展开, Enter发送, q退出)"
        if h < 6 or w < 20:
            _safe_addnstr(
                stdscr,
                0,
                0,
                "窗口太小，请放大终端 (min 20x6)。",
                w,
            )
            stdscr.refresh()
            time.sleep(0.1)
            continue
        _safe_addnstr(stdscr, 0, 0, header.ljust(w), w)

        main_height = max(1, h - 4)
        if state.view_mode == "nodes":
            _render_nodes_view(stdscr, state, 1, main_height, w)
        else:
            _render_chat_view(stdscr, state, 1, main_height, w)

        log_lines = state.system_log[-2:] if state.system_log else []
        log_lines = [""] * (2 - len(log_lines)) + log_lines
        _safe_addnstr(stdscr, h - 3, 0, log_lines[0].ljust(w), w)
        _safe_addnstr(stdscr, h - 2, 0, log_lines[1].ljust(w), w)
        prompt = "> " + input_buffer
        _safe_addnstr(stdscr, h - 1, 0, prompt[-w:].ljust(w), w)
        stdscr.refresh()

        ch = stdscr.getch()
        if ch == -1:
            time.sleep(0.05)
            continue
        if ch in (ord("q"), ord("Q")):
            break
        if ch in (9, curses.KEY_BTAB):
            state.view_mode = "chat" if state.view_mode == "nodes" else "nodes"
            continue
        if state.view_mode == "nodes":
            if ch == curses.KEY_UP:
                state.selected_index = max(0, state.selected_index - 1)
                continue
            if ch == curses.KEY_DOWN:
                state.selected_index = min(len(state.node_order) - 1, state.selected_index + 1)
                continue
            if ch == ord(" "):
                node = state.node_order[state.selected_index]
                state.nodes[node].expanded = not state.nodes[node].expanded
                continue

        if state.running:
            continue

        if ch in (curses.KEY_ENTER, 10, 13):
            question = input_buffer.strip()
            input_buffer = ""
            if not question:
                continue

            now = dt.datetime.now()
            append_event(convo_path, {"ts": now.isoformat(), "type": "user_message", "text": question})
            sink({"type": "user_message", "text": question})

            def worker() -> None:
                result = run_turn(profile, question, now=now, event_sink=sink, stream=True)
                append_event(convo_path, {"ts": now.isoformat(), "type": "plan", "plan": result["plan"]})
                if result["time_context"]:
                    append_event(convo_path, {"ts": now.isoformat(), "type": "time_context", "value": result["time_context"]})
                append_event(convo_path, {"ts": now.isoformat(), "type": "assistant_final", "text": result["response"]})
                save_profile(profile_path, profile)
                sink({"type": "assistant_final", "text": result["response"]})

            running_thread = threading.Thread(target=worker, daemon=True)
            running_thread.start()
            continue
        if ch in (curses.KEY_BACKSPACE, 127, 8):
            input_buffer = input_buffer[:-1]
            continue
        if 32 <= ch <= 126:
            input_buffer += chr(ch)


def main() -> None:
    user_id, profile, profile_path = _select_user()
    convo_path = _select_conversation(user_id)
    curses.wrapper(_run_chat_ui, profile, profile_path, convo_path, user_id)


if __name__ == "__main__":
    main()
