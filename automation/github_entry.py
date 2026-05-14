# -*- coding: utf-8 -*-

import os
import sys
import traceback
import importlib.util
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

try:
    from send_email import send_email
except ModuleNotFoundError:
    from automation.send_email import send_email


# =========================
# 仓库根目录
# =========================
REPO_ROOT = Path(__file__).resolve().parent.parent

# 输出目录：统一使用 outputs
OUTPUT_DIR = REPO_ROOT / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# 数据目录
DATA_DIR = REPO_ROOT / "data"


# =========================
# 新加坡时间日期
# =========================
def get_sg_today():
    sg_tz = ZoneInfo("Asia/Singapore")
    now = datetime.now(sg_tz)
    return now.strftime("%Y%m%d")


# =========================
# 日期解析
# =========================
def split_dates(raw: str):
    dates = []
    if not raw:
        return dates

    for part in raw.replace(";", ",").replace("\n", ",").split(","):
        s = part.strip()
        if s and s.isdigit() and len(s) == 8:
            dates.append(s)

    return sorted(set(dates))


def get_target_dates():
    """
    优先读取 TARGET_DATES；
    如果没有 TARGET_DATES，则读取 TARGET_DATE；
    如果都没有，则使用新加坡当天日期。
    """
    raw_multi = os.getenv("TARGET_DATES", "").strip()

    if raw_multi:
        dates = split_dates(raw_multi)
    else:
        raw_single = os.getenv("TARGET_DATE", get_sg_today()).strip()
        dates = split_dates(raw_single)

    if not dates:
        raise RuntimeError("TARGET_DATE / TARGET_DATES 日期格式错误，必须是 YYYYMMDD，例如 20260513")

    return dates


# =========================
# 可选整数环境变量
# =========================
def get_optional_int_env(name: str):
    raw = os.getenv(name)

    if raw is None:
        return None

    raw = raw.strip()

    if raw == "" or raw.lower() in {"none", "null"}:
        return None

    value = int(raw)

    # TEST_LIMIT=0 时容易导致扫描 0 只股票，这里按“不限制”处理
    if name == "TEST_LIMIT" and value <= 0:
        return None

    return value


# =========================
# 动态加载策略脚本
# =========================
def load_strategy_module(script_path: Path):
    if not script_path.exists():
        raise RuntimeError(f"无法加载策略脚本，文件不存在: {script_path}")

    spec = importlib.util.spec_from_file_location(
        "scan_strategy_runtime",
        str(script_path)
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法创建模块 spec: {script_path}")

    mod = importlib.util.module_from_spec(spec)
    sys.modules["scan_strategy_runtime"] = mod
    spec.loader.exec_module(mod)

    return mod


# =========================
# 注入策略脚本配置
# =========================
def apply_strategy_config(mod, target_dates, end_date):
    """
    兼容新版 three_bar_play_multi_dates.py，
    同时也兼容旧版 scan_strategy.py 的全局变量写法。
    """

    # Tushare Token
    setattr(mod, "TUSHARE_TOKEN", os.getenv("TUSHARE_TOKEN", "").strip())

    # 日期
    setattr(mod, "TARGET_DATES", list(target_dates))
    setattr(mod, "END_DATE", end_date)

    if os.getenv("START_DATE"):
        setattr(mod, "START_DATE", os.getenv("START_DATE").strip())

    # 数据目录 / 输出目录
    setattr(mod, "DATA_DIR", str(DATA_DIR))
    setattr(mod, "OUTPUT_DIR", str(OUTPUT_DIR))

    # 数据文件
    setattr(
        mod,
        "CODE_FILE",
        str(DATA_DIR / "a_share_codes_for_akshare.csv")
    )

    setattr(
        mod,
        "BELOW_8B_FILE",
        str(DATA_DIR / "a_share_below_8b.csv")
    )

    setattr(
        mod,
        "ST_FILE",
        str(DATA_DIR / "st_stocks.csv")
    )

    # 兼容旧版脚本的固定输出文件名
    setattr(
        mod,
        "OUTPUT_FILE",
        str(OUTPUT_DIR / f"candidates_{end_date}.csv")
    )

    setattr(
        mod,
        "DEBUG_FILE",
        str(OUTPUT_DIR / f"debug_{end_date}.csv")
    )

    setattr(
        mod,
        "FAILED_FILE",
        str(OUTPUT_DIR / f"failed_{end_date}.csv")
    )

    setattr(
        mod,
        "FILTERED_FILE",
        str(OUTPUT_DIR / f"filtered_{end_date}.csv")
    )

    # 可选运行参数
    max_workers = get_optional_int_env("MAX_WORKERS")
    if max_workers is not None:
        setattr(mod, "MAX_WORKERS", max_workers)

    test_limit = get_optional_int_env("TEST_LIMIT")
    setattr(mod, "TEST_LIMIT", test_limit)

    batch_start = get_optional_int_env("BATCH_START")
    if batch_start is not None:
        setattr(mod, "BATCH_START", batch_start)

    batch_size = get_optional_int_env("BATCH_SIZE")
    if batch_size is not None:
        setattr(mod, "BATCH_SIZE", batch_size)

    if os.getenv("SLEEP_SEC"):
        setattr(mod, "SLEEP_SEC", float(os.getenv("SLEEP_SEC")))


# =========================
# 查找输出文件
# =========================
def find_output_files(end_date: str):
    """
    兼容两种输出命名：
    1. 新版 three_bar_play_multi_dates.py:
       three_bar_play_resting_candidates_YYYYMMDD.csv
    2. 旧版 github_entry.py:
       candidates_YYYYMMDD.csv
    """

    search_dirs = [
        OUTPUT_DIR,
        REPO_ROOT / "output",
        REPO_ROOT / "outputs",
    ]

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

    for d in search_dirs:
        if not d.exists():
            continue

        for pattern in patterns:
            for p in d.glob(pattern):
                if p.is_file() and p not in files:
                    files.append(p)

    return files


def pick_candidates_file(files, end_date: str):
    preferred_names = [
        f"three_bar_play_resting_candidates_{end_date}.csv",
        f"candidates_{end_date}.csv",
    ]

    for name in preferred_names:
        for p in files:
            if p.name == name:
                return p

    for p in files:
        if "candidate" in p.name.lower() or "candidates" in p.name.lower():
            return p

    return None


# =========================
# 主函数
# =========================
def main():

    # -------------------------
    # 日期
    # -------------------------
    target_dates = get_target_dates()
    end_date = max(target_dates)

    # 同步给策略脚本读取
    os.environ["TARGET_DATE"] = end_date
    os.environ["TARGET_DATES"] = ",".join(target_dates)

    # -------------------------
    # 策略脚本路径
    # -------------------------
    script_name = os.getenv(
        "SCAN_SCRIPT_PATH",
        "three_bar_play_multi_dates.py"
    ).strip()

    script_path = Path(script_name)

    if not script_path.is_absolute():
        script_path = REPO_ROOT / script_name

    print("=" * 80)
    print(f"仓库根目录: {REPO_ROOT}")
    print(f"策略脚本路径: {script_path}")
    print(f"目标日期列表: {target_dates}")
    print(f"END_DATE: {end_date}")
    print(f"数据目录: {DATA_DIR}")
    print(f"输出目录: {OUTPUT_DIR}")
    print("=" * 80)

    # -------------------------
    # 基础检查
    # -------------------------
    if not os.getenv("TUSHARE_TOKEN", "").strip():
        raise RuntimeError("未检测到 TUSHARE_TOKEN，请在 GitHub Secrets 中配置 TUSHARE_TOKEN")

    required_data_files = [
        DATA_DIR / "a_share_codes_for_akshare.csv",
        DATA_DIR / "a_share_below_8b.csv",
        DATA_DIR / "st_stocks.csv",
    ]

    for f in required_data_files:
        if not f.exists():
            raise RuntimeError(f"缺少数据文件: {f}")

    # -------------------------
    # 加载策略脚本
    # -------------------------
    mod = load_strategy_module(script_path)

    # -------------------------
    # 注入配置
    # -------------------------
    apply_strategy_config(mod, target_dates, end_date)

    # -------------------------
    # 检查 main
    # -------------------------
    if not hasattr(mod, "main"):
        raise RuntimeError("策略脚本中未找到 main() 函数")

    # -------------------------
    # 执行策略
    # -------------------------
    print("\n开始运行策略...\n")

    mod.main()

    print("\n策略运行完成\n")

    # -------------------------
    # 输出文件检查
    # -------------------------
    output_files = find_output_files(end_date)
    candidates_file = pick_candidates_file(output_files, end_date)

    print("\n已发现输出文件：")
    if output_files:
        for p in output_files:
            print(f"- {p}")
    else:
        print("未发现任何输出 CSV 文件")

    # -------------------------
    # 邮件正文
    # -------------------------
    if candidates_file and candidates_file.exists():

        print(f"\n候选结果文件存在: {candidates_file}")

        try:
            import pandas as pd

            df = pd.read_csv(candidates_file)
            row_count = len(df)

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

        except Exception as e:

            email_body = f"""
Three Bar Play Daily Scan 完成

日期:
{end_date}

目标日期列表:
{", ".join(target_dates)}

候选结果文件:
{candidates_file.name}

但读取 CSV 失败:
{e}

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

请检查策略脚本是否正常输出 CSV。
GitHub Actions 自动发送
"""

    # -------------------------
    # 发送邮件
    # -------------------------
    print("\n开始发送邮件...\n")

    attachments = [str(p) for p in output_files if p.exists()]

    send_email(
        subject=f"[ThreeBar] {end_date} Daily Scan",
        body=email_body,
        attachments=attachments
    )

    print("\n邮件发送完成\n")


# =========================
# 程序入口
# =========================
if __name__ == "__main__":

    try:

        main()

    except Exception:

        error_msg = traceback.format_exc()

        print(error_msg)

        try:

            send_email(
                subject="[ThreeBar] Scan Failed",
                body=f"""
GitHub Actions 扫描失败

错误信息:

{error_msg}
"""
            )

        except Exception as mail_err:

            print(f"发送失败邮件也失败: {mail_err}")

        raise
