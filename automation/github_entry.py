from __future__ import annotations

import importlib.util
import os
import traceback
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from send_email import send_email

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_strategy_module(script_path: Path):
    spec = importlib.util.spec_from_file_location("scan_strategy_module", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载策略脚本: {script_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sg_today_str() -> str:
    now_sg = datetime.now(ZoneInfo("Asia/Singapore"))
    return now_sg.strftime("%Y%m%d")


def env_or_none(name: str):
    v = os.environ.get(name)
    return v if v not in (None, "") else None


def maybe_set(mod, name: str, value):
    if hasattr(mod, name) and value is not None:
        setattr(mod, name, value)


def configure_strategy(mod, target_date: str) -> dict[str, Path]:
    out_date_dir = OUTPUT_DIR / target_date
    out_date_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "OUTPUT_FILE": out_date_dir / f"candidates_{target_date}.csv",
        "DEBUG_FILE": out_date_dir / f"debug_{target_date}.csv",
        "FAILED_FILE": out_date_dir / f"failed_{target_date}.csv",
        "FILTERED_FILE": out_date_dir / f"filtered_{target_date}.csv",
    }

    maybe_set(mod, "TUSHARE_TOKEN", os.environ.get("TUSHARE_TOKEN"))
    maybe_set(mod, "TARGET_DATES", [target_date])
    maybe_set(mod, "END_DATE", target_date)

    maybe_set(mod, "OUTPUT_FILE", str(paths["OUTPUT_FILE"]))
    maybe_set(mod, "DEBUG_FILE", str(paths["DEBUG_FILE"]))
    maybe_set(mod, "FAILED_FILE", str(paths["FAILED_FILE"]))
    maybe_set(mod, "FILTERED_FILE", str(paths["FILTERED_FILE"]))

    maybe_set(mod, "CODE_FILE", env_or_none("CODE_FILE") or str(REPO_ROOT / "data" / "a_share_codes_for_akshare.csv"))
    maybe_set(mod, "BELOW_8B_FILE", env_or_none("BELOW_8B_FILE") or str(REPO_ROOT / "data" / "a_share_below_8b.csv"))
    maybe_set(mod, "ST_FILE", env_or_none("ST_FILE") or str(REPO_ROOT / "data" / "st_stocks.csv"))

    maybe_set(mod, "START_DATE", env_or_none("START_DATE"))
    if env_or_none("MAX_WORKERS"):
        maybe_set(mod, "MAX_WORKERS", int(os.environ["MAX_WORKERS"]))
    if env_or_none("BATCH_START"):
        maybe_set(mod, "BATCH_START", int(os.environ["BATCH_START"]))
    if env_or_none("BATCH_SIZE"):
        maybe_set(mod, "BATCH_SIZE", int(os.environ["BATCH_SIZE"]))
    if env_or_none("TEST_LIMIT"):
        maybe_set(mod, "TEST_LIMIT", int(os.environ["TEST_LIMIT"]))
    if env_or_none("SLEEP_SEC"):
        maybe_set(mod, "SLEEP_SEC", float(os.environ["SLEEP_SEC"]))

    return paths


def summarize_csv(path: Path) -> str:
    if not path.exists():
        return f"- {path.name}: 未生成"
    try:
        df = pd.read_csv(path)
    except Exception as e:
        return f"- {path.name}: 读取失败: {e}"
    lines = [f"- {path.name}: {len(df)} 行"]
    if len(df) > 0:
        cols = [c for c in ["ticker", "name", "signal_type", "setup_type", "grade_tier", "total_score", "target_date"] if c in df.columns]
        preview = df[cols].head(10)
        lines.append(preview.to_string(index=False))
    return "\n".join(lines)


def main() -> int:
    target_date = os.environ.get("TARGET_DATE") or sg_today_str()
    script_rel = os.environ.get("SCAN_SCRIPT_PATH", "scan_strategy.py")
    script_path = (REPO_ROOT / script_rel).resolve()

    subject_prefix = os.environ.get("EMAIL_SUBJECT_PREFIX", "[ThreeBar]")
    subject = f"{subject_prefix} Daily Scan {target_date}"

    if not script_path.exists():
        body = f"策略脚本不存在: {script_path}"
        send_email(subject + " FAILED", body)
        return 1

    try:
        mod = load_strategy_module(script_path)
        paths = configure_strategy(mod, target_date)
        if not hasattr(mod, "main"):
            raise RuntimeError("策略脚本缺少 main() 函数")
        mod.main()

        body_parts = [
            f"扫描完成：{target_date}",
            "",
            summarize_csv(paths["OUTPUT_FILE"]),
            "",
            summarize_csv(paths["DEBUG_FILE"]),
            "",
            summarize_csv(paths["FAILED_FILE"]),
        ]
        body = "\n".join(body_parts)
        attachments = [p for p in paths.values() if p.exists()]
        send_email(subject, body, attachments)
        print(body)
        return 0
    except Exception:
        tb = traceback.format_exc()
        body = f"扫描失败：{target_date}\n\n{tb}"
        try:
            send_email(subject + " FAILED", body)
        except Exception:
            print("发送失败通知邮件也失败了。")
        print(body)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
