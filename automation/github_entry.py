# -*- coding: utf-8 -*-

import os
import sys
import traceback
import subprocess
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo


# =========================
# 兼容邮件密码变量名
# =========================
# 你的 GitHub Secrets 里是 SMTP_PASS；有些 send_email.py 可能读取 SMTP_PASSWORD。
# 所以这里在导入 send_email 之前先做映射。
if not os.getenv("SMTP_PASSWORD") and os.getenv("SMTP_PASS"):
    os.environ["SMTP_PASSWORD"] = os.getenv("SMTP_PASS", "")

try:
    from send_email import send_email
except ModuleNotFoundError:
    from automation.send_email import send_email


# =========================
# 仓库目录

# 兼容邮件变量名
if not os.getenv("SMTP_PASSWORD") and os.getenv("SMTP_PASS"):
    os.environ["SMTP_PASSWORD"] = os.getenv("SMTP_PASS")

if not os.getenv("SMTP_PASS") and os.getenv("SMTP_PASSWORD"):
    os.environ["SMTP_PASS"] = os.getenv("SMTP_PASSWORD")

if not os.getenv("EMAIL_TO") and os.getenv("MAIL_TO"):
    os.environ["EMAIL_TO"] = os.getenv("MAIL_TO")

if not os.getenv("MAIL_TO") and os.getenv("EMAIL_TO"):
    os.environ["MAIL_TO"] = os.getenv("EMAIL_TO")

# =========================
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
OUTPUTS_DIR = REPO_ROOT / "outputs"
OUTPUT_DIR = REPO_ROOT / "output"

OUTPUTS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


# =========================
# 中国日期
# =========================
def get_cn_today() -> str:
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    return now.strftime("%Y%m%d")


def split_dates(raw: str):
    if not raw:
        return []

    dates = []
    for part in raw.replace(";", ",").replace("\n", ",").split(","):
        s = part.strip()
        if s and s.isdigit() and len(s) == 8:
            dates.append(s)

    return sorted(set(dates))


def get_target_dates():
    raw_multi = (os.getenv("TARGET_DATES") or "").strip()
    raw_single = (os.getenv("TARGET_DATE") or "").strip()

    if raw_multi:
        dates = split_dates(raw_multi)
    elif raw_single:
        dates = split_dates(raw_single)
    else:
        dates = [get_cn_today()]

    if not dates:
        raise RuntimeError("日期格式错误：TARGET_DATE / TARGET_DATES 必须是 YYYYMMDD，例如 20260514")

    return dates


# =========================
# 环境变量工具
# =========================
def env_text(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def ensure_required_env():
    required = [
        "TUSHARE_TOKEN",
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USER",
        "SMTP_PASS",
        "MAIL_TO",
    ]

    missing = [name for name in required if not env_text(name)]
    if missing:
        raise RuntimeError(f"GitHub Secrets / 环境变量缺失: {missing}")


def build_strategy_env(target_dates, end_date):
    env = os.environ.copy()

    # 统一日期变量
    env["TARGET_DATES"] = ",".join(target_dates)
    env["TARGET_DATE"] = end_date

    # 你的 Secrets 名保持 SMTP_PASS，同时兼容 SMTP_PASSWORD。
    if not env.get("SMTP_PASSWORD") and env.get("SMTP_PASS"):
        env["SMTP_PASSWORD"] = env["SMTP_PASS"]

    # 给主策略脚本设置安全默认值，避免空字符串 int('') 报错。
    defaults = {
        "START_DATE": "20240301",
        "MAX_WORKERS": "1",
        "TEST_LIMIT": "",
        "BATCH_START": "0",
        "BATCH_SIZE": "10000",
        "SLEEP_SEC": "0.10",
    }

    for key, value in defaults.items():
        if not (env.get(key) or "").strip():
            env[key] = value

    return env


# =========================
# 文件检查
# =========================
def get_script_path() -> Path:
    script_name = env_text("SCAN_SCRIPT_PATH", "three_bar_play_multi_dates.py")
    if not script_name:
        script_name = "three_bar_play_multi_dates.py"

    script_path = Path(script_name)
    if not script_path.is_absolute():
        script_path = REPO_ROOT / script_name

    if not script_path.exists():
        raise RuntimeError(f"策略脚本不存在: {script_path}")

    if script_path.is_dir():
        raise RuntimeError(f"策略脚本路径指向文件夹，不是 .py 文件: {script_path}")

    if script_path.suffix.lower() != ".py":
        raise RuntimeError(f"策略脚本不是 .py 文件: {script_path}")

    return script_path


def check_data_files():
    required_files = [
        DATA_DIR / "a_share_codes_for_akshare.csv",
        DATA_DIR / "a_share_below_8b.csv",
        DATA_DIR / "st_stocks.csv",
    ]

    for path in required_files:
        if not path.exists():
            raise RuntimeError(f"缺少数据文件: {path}")


# =========================
# 输出文件查找
# =========================
def find_output_files(end_date: str):
    search_dirs = [OUTPUTS_DIR, OUTPUT_DIR]
    patterns = [
        f"three_bar_play_resting_candidates_{end_date}.csv",
        f"three_bar_play_resting_debug_rejected_{end_date}.csv",
        f"three_bar_play_resting_failed_fetch_{end_date}.csv",
        f"three_bar_play_resting_filtered_out_{end_date}.csv",
        f"candidates_{end_date}.csv",
        f"debug_{end_date}.csv",
        f"failed_{end_date}.csv",
        f"filtered_{end_date}.csv",
        f"*{end_date}*.csv",
    ]

    files = []
    for directory in search_dirs:
        if not directory.exists():
            continue
        for pattern in patterns:
            for path in directory.glob(pattern):
                if path.is_file() and path not in files:
                    files.append(path)

    return files


def pick_candidates_file(files, end_date: str):
    preferred = [
        f"three_bar_play_resting_candidates_{end_date}.csv",
        f"candidates_{end_date}.csv",
    ]

    for name in preferred:
        for path in files:
            if path.name == name:
                return path

    for path in files:
        lower = path.name.lower()
        if "candidate" in lower or "candidates" in lower:
            return path

    return None


# =========================
# 邮件发送
# =========================
def safe_send_email(subject: str, body: str, attachments=None):
    if attachments is None:
        attachments = []

    # 再做一次变量兼容，防止 send_email.py 在函数内部读取 SMTP_PASSWORD。
    if not os.getenv("SMTP_PASSWORD") and os.getenv("SMTP_PASS"):
        os.environ["SMTP_PASSWORD"] = os.getenv("SMTP_PASS", "")

    try:
        send_email(
            subject=subject,
            body=body,
            attachments=attachments,
        )
    except Exception as e:
        print(f"发送邮件失败: {type(e).__name__}: {e}")


# =========================
# 主函数
# =========================
def main():
    target_dates = get_target_dates()
    end_date = max(target_dates)
    script_path = get_script_path()

    print("=" * 80)
    print(f"仓库根目录: {REPO_ROOT}")
    print(f"策略脚本路径: {script_path}")
    print(f"目标日期列表: {target_dates}")
    print(f"END_DATE: {end_date}")
    print(f"数据目录: {DATA_DIR}")
    print(f"输出目录1 outputs: {OUTPUTS_DIR}")
    print(f"输出目录2 output: {OUTPUT_DIR}")
    print("=" * 80)

    ensure_required_env()
    check_data_files()

    env = build_strategy_env(target_dates, end_date)

    print("\n开始运行策略脚本...\n")
    subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(REPO_ROOT),
        env=env,
        check=True,
    )
    print("\n策略脚本运行完成。\n")

    output_files = find_output_files(end_date)
    candidates_file = pick_candidates_file(output_files, end_date)

    print("\n已发现输出文件：")
    if output_files:
        for path in output_files:
            print(f"- {path}")
    else:
        print("未发现任何输出 CSV 文件。")

    if candidates_file and candidates_file.exists():
        try:
            import pandas as pd
            df = pd.read_csv(candidates_file)
            row_count = len(df)
        except Exception as e:
            row_count = "读取失败"
            print(f"读取候选文件失败: {type(e).__name__}: {e}")

        email_body = f"""
Three Bar Play Daily Scan 完成

日期:
{end_date}

目标日期列表:
{", ".join(target_dates)}

候选股票数量:
{row_count}

候选结果文件:
{candidates_file.name}

输出文件数量:
{len(output_files)}

GitHub Actions 自动发送
"""
    else:
        email_body = f"""
Three Bar Play Daily Scan 完成

日期:
{end_date}

目标日期列表:
{", ".join(target_dates)}

但未发现候选结果文件。
请检查主策略脚本是否正常输出 CSV。

GitHub Actions 自动发送
"""

    attachments = [str(path) for path in output_files if path.exists()]

    print("\n开始发送邮件...\n")
    safe_send_email(
        subject=f"[ThreeBar] {end_date} Daily Scan",
        body=email_body,
        attachments=attachments,
    )
    print("\n邮件处理完成。\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        error_msg = traceback.format_exc()
        print(error_msg)

        safe_send_email(
            subject="[ThreeBar] Scan Failed",
            body=f"""
GitHub Actions 扫描失败

错误信息:

{error_msg}
""",
            attachments=[],
        )

        raise
