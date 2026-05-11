"""
把你自己的扫描脚本重命名为 scan_strategy.py 覆盖这个文件，
或者在 GitHub Secrets 里设置 SCAN_SCRIPT_PATH 指向你的脚本路径。

要求：
1. 脚本中存在 main() 函数。
2. 如果脚本使用了这些全局变量，包装器会自动覆盖：
   - TUSHARE_TOKEN
   - TARGET_DATES
   - END_DATE
   - OUTPUT_FILE / DEBUG_FILE / FAILED_FILE / FILTERED_FILE
   - CODE_FILE / BELOW_8B_FILE / ST_FILE
   - START_DATE / MAX_WORKERS / BATCH_START / BATCH_SIZE / TEST_LIMIT
"""

raise RuntimeError("请用你自己的扫描脚本覆盖 scan_strategy.py，或设置 SCAN_SCRIPT_PATH。")
