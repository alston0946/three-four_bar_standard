import os
import sys
import traceback
import importlib.util
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from automation.send_email import send_email


# =========================
# 仓库根目录
# =========================
REPO_ROOT = Path(__file__).resolve().parent.parent

# 输出目录
OUTPUT_DIR = REPO_ROOT / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# 数据目录
DATA_DIR = REPO_ROOT / "data"


# =========================
# 动态加载策略脚本
# =========================
def load_strategy_module(script_path: str):
    script_path = Path(script_path)

    if not script_path.exists():
        raise RuntimeError(f"无法加载策略脚本: {script_path}")

    spec = importlib.util.spec_from_file_location(
        "scan_strategy",
        str(script_path)
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法创建模块 spec: {script_path}")

    mod = importlib.util.module_from_spec(spec)

    sys.modules["scan_strategy"] = mod

    spec.loader.exec_module(mod)

    return mod


# =========================
# 新加坡时间日期
# =========================
def get_sg_today():
    sg_tz = ZoneInfo("Asia/Singapore")
    now = datetime.now(sg_tz)
    return now.strftime("%Y%m%d")


# =========================
# 主函数
# =========================
def main():

    # -------------------------
    # 日期
    # -------------------------
    target_date = os.getenv("TARGET_DATE", get_sg_today())

    # -------------------------
    # 策略脚本路径
    # -------------------------
    script_name = os.getenv(
        "SCAN_SCRIPT_PATH",
        "scan_strategy.py"
    )

    script_path = REPO_ROOT / script_name

    print("=" * 80)
    print(f"仓库根目录: {REPO_ROOT}")
    print(f"策略脚本路径: {script_path}")
    print(f"目标日期: {target_date}")
    print("=" * 80)

    # -------------------------
    # 加载策略脚本
    # -------------------------
    mod = load_strategy_module(str(script_path))

    # -------------------------
    # 注入环境变量
    # -------------------------
    setattr(mod, "TUSHARE_TOKEN", os.getenv("TUSHARE_TOKEN", ""))

    setattr(mod, "TARGET_DATES", [target_date])
    setattr(mod, "END_DATE", target_date)

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

    # 输出文件
    setattr(
        mod,
        "OUTPUT_FILE",
        str(OUTPUT_DIR / f"candidates_{target_date}.csv")
    )

    setattr(
        mod,
        "DEBUG_FILE",
        str(OUTPUT_DIR / f"debug_{target_date}.csv")
    )

    setattr(
        mod,
        "FAILED_FILE",
        str(OUTPUT_DIR / f"failed_{target_date}.csv")
    )

    setattr(
        mod,
        "FILTERED_FILE",
        str(OUTPUT_DIR / f"filtered_{target_date}.csv")
    )

    # 可选参数
    setattr(
        mod,
        "MAX_WORKERS",
        int(os.getenv("MAX_WORKERS", "8"))
    )

    setattr(
        mod,
        "TEST_LIMIT",
        int(os.getenv("TEST_LIMIT", "0"))
    )

    # -------------------------
    # 检查 main
    # -------------------------
    if not hasattr(mod, "main"):
        raise RuntimeError(
            "策略脚本中未找到 main() 函数"
        )

    # -------------------------
    # 执行策略
    # -------------------------
    print("\n开始运行策略...\n")

    mod.main()

    print("\n策略运行完成\n")

    # -------------------------
    # 输出文件检查
    # -------------------------
    output_file = OUTPUT_DIR / f"candidates_{target_date}.csv"

    if output_file.exists():

        print(f"输出文件存在: {output_file}")

        try:
            import pandas as pd

            df = pd.read_csv(output_file)

            row_count = len(df)

            email_body = f"""
Three Bar Play Daily Scan 完成

日期:
{target_date}

候选股票数量:
{row_count}

输出文件:
{output_file.name}

GitHub Actions 自动发送
"""

        except Exception as e:

            email_body = f"""
Three Bar Play Daily Scan 完成

日期:
{target_date}

但读取 CSV 失败:
{e}
"""

    else:

        email_body = f"""
Three Bar Play Daily Scan 完成

日期:
{target_date}

但未发现输出文件:
{output_file.name}
"""

    # -------------------------
    # 发送邮件
    # -------------------------
    print("\n开始发送邮件...\n")

    send_email(
        subject=f"[ThreeBar] {target_date} Daily Scan",
        body=email_body,
        attachments=[str(output_file)] if output_file.exists() else []
    )

    print("\n邮件发送完成\n")


# =========================
# 程序入口
# =========================
if __name__ == "__main__":

    try:

        main()

    except Exception as e:

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
