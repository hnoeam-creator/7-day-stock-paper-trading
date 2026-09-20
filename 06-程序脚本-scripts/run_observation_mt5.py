#!/usr/bin/env python3
"""Six-slot, read-only MT5 runner with locking, duplicate prevention and export recovery (Windows compatible)."""
import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
# Windows-compatible file locking
if sys.platform == "win32":
    import msvcrt
else:
    import fcntl
# Add project root to path
scripts_dir = str(Path(__file__).resolve().parent)
sys.path.insert(0, scripts_dir)
print(f"DEBUG: scripts_dir = {scripts_dir}")
print(f"DEBUG: sys.path[0] = {sys.path[0]}")
print(f"DEBUG: files in scripts_dir = {list(Path(scripts_dir).glob('*.py'))}")

from mt5_readiness_check import CONFIG as MT5_CONFIG, ROOT, check_mt5, load_config as load_mt5_config, update_readiness as update_mt5_readiness

from mt5_readiness_check import CONFIG as MT5_CONFIG, ROOT, check_mt5, load_config as load_mt5_config, update_readiness as update_mt5_readiness
from run_store import RunStore, utc_now
STARTUP = ("AGENTS.md", "AGENTS.zh-CN.md", "02-项目文档-docs/TRADING-STRATEGY.md", "02-项目文档-docs/TRADING-STRATEGY.zh-CN.md",
           "03-定时任务-routines/schedule.json", "03-定时任务-routines/schedule.zh-CN.json", "03-定时任务-routines/CONTINUITY.md",
           "03-定时任务-routines/CONTINUITY.zh-CN.md", "04-运行状态-state/readiness.json", "05-交易记录-data/current-state-mt5.json")
class FileLock:
    """Cross-platform file locking."""
    def __init__(self, path):
        self.path = Path(path)
        self.handle = None
    
    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = open(self.path, "a")
        if sys.platform == "win32":
            msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return self
    
    def __exit__(self, *args):
        try:
            if sys.platform == "win32":
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        finally:
            self.handle.close()
def due_slot(schedule, now):
    local = now.astimezone(ZoneInfo(schedule["timezone"]))
    if local.date().isoformat() not in schedule["planned_trading_dates"]:
        return None
    candidates = []
    for task in schedule["tasks"]:
        hour, minute = map(int, task["time"].split(":"))
        planned = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        delay = local - planned
        if timedelta(0) <= delay <= timedelta(minutes=schedule["late_start_grace_minutes"]):
            candidates.append((delay, task["id"]))
    if candidates:
        _, task_id = min(candidates, key=lambda candidate: candidate[0])
        return local.date().isoformat() + "_" + task_id
    return None
def atomic_write(path, text):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as file:
            temporary = Path(file.name)
            file.write(text)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
def export_records(store):
    records = store.completed()
    for run_id, payload in records:
        atomic_write(ROOT / "05-交易记录-data" / "journal" / (run_id + ".md"), payload["journal"])
        atomic_write(ROOT / "05-交易记录-data" / "evidence" / (run_id + ".json"), json.dumps(payload["check"], indent=2) + "\n")
    if records:
        run_id, payload = records[-1]
        path = ROOT / "05-交易记录-data" / "current-state-mt5.json"
        state = json.loads(path.read_text(encoding="utf-8"))
        latest = state.get("last_run") or {}
        timestamp = payload["check"]["checked_at"]
        if latest.get("timestamp", "") <= timestamp:
            state["last_run"] = {"run_id": run_id, "timestamp": timestamp, "mode": "observation_only_mt5",
                                 "mt5_api_verified": payload["check"].get("account_read_verified", False) and payload["check"].get("symbol_tick_read_verified", False), "orders_placed": False}
            atomic_write(path, json.dumps(state, ensure_ascii=False, indent=2) + "\n")
def make_payload(run_id, check, state):
    journal = "\n".join([
        "# Read-only MT5 observation / 只读MT5观察", "", "- Run: " + run_id,
        "- Timestamp: " + utc_now(),
        "- Action / 本次操作: Read Pepperstone MT5 API and record actual verification results.",
        "- Reason / 原因: Verify data and account access before experiment execution.",
        "- Order proposed / 提出订单: no", "- Order placed / 提交订单: no", "- Order filled / 成交: no",
        "- Local paper holdings / 本地模拟持仓: " + json.dumps(state.get("positions", []), ensure_ascii=False),
        "- Local paper cash / 本地模拟现金 USD: " + str(state.get("cash")),
        "- Local paper risk / 本地模拟未平仓风险 USD: " + str(state.get("daily_open_risk")),
        "- Real account holdings and cash / 真实账户资产: not reconciled by this checker.",
        "- Errors / 检查问题: " + json.dumps(check.get("errors", [])),
        "- Next / 下次重点: Resolve authentication, verify MT5 data and review risk limits.",
        "- Human input / 人工事项: Local MT5 settings if authentication fails; review risk config.",
        "- Evidence: ../evidence/" + run_id + ".json", "",
    ])
    return {"journal": journal, "check": check}
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--manual", action="store_true")
    group.add_argument("--recover", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--symbol", default="EURUSD", help="Symbol to check (default: EURUSD)")
    args = parser.parse_args()
    
    schedule = json.loads((ROOT / "03-定时任务-routines/schedule.json").read_text(encoding="utf-8"))
    slot = due_slot(schedule, datetime.now(ZoneInfo("UTC")))
    
    if args.dry_run:
        print(json.dumps({"due_slot": slot, "planned_slots": len(schedule["planned_trading_dates"]) * len(schedule["tasks"])}))
        return 0
    
    if not args.manual and not args.recover and slot is None:
        print(json.dumps({"status": "outside_scheduled_window"}))
        return 0
    
    lock_path = ROOT / "04-运行状态-state" / "run.lock"
    with FileLock(lock_path) as lock:
        store = RunStore(ROOT / "05-交易记录-data" / "runs.sqlite3")
        try:
            export_records(store)
            if args.recover:
                count = store.recover_read_only()
                print(json.dumps({"interrupted_runs_recorded": count, "exports_restored": True}))
                return 0
            
            for name in STARTUP:
                (ROOT / name).read_text(encoding="utf-8")
            
            journals = sorted((ROOT / "05-交易记录-data" / "journal").glob("*.md"), key=lambda p: p.stat().st_mtime)
            if journals:
                journals[-1].read_text(encoding="utf-8")
            
            run_id = "manual_mt5_" + datetime.now().strftime("%Y%m%dT%H%M%S%f") if args.manual else slot + "_mt5"
            if not store.begin(run_id):
                print(json.dumps({"status": "duplicate_skipped", "run_id": run_id}))
                return 0
            
            state = json.loads((ROOT / "05-交易记录-data" / "current-state-mt5.json").read_text(encoding="utf-8"))
            config = load_mt5_config(MT5_CONFIG)
            result = check_mt5(config, symbol=args.symbol)
            update_mt5_readiness(result)
            
            store.finish(run_id, make_payload(run_id, result, state))
            export_records(store)
            
            print(json.dumps({"run_id": run_id, "mt5_account_verified": result["account_read_verified"], "mt5_market_verified": result["symbol_tick_read_verified"], "errors": result["errors"]}, indent=2))
            return 0 if result["account_read_verified"] and result["symbol_tick_read_verified"] else 2
        finally:
            store.close()
if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError):
        print(json.dumps({"error": "MT5 Observation incomplete; inspect local state and use --recover before next run"}))
        raise SystemExit(4)
