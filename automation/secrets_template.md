# GitHub Secrets 清单

在仓库 Settings -> Secrets and variables -> Actions 中添加：

## 必填
- TUSHARE_TOKEN
- EMAIL_TO
- SMTP_HOST
- SMTP_PORT
- SMTP_USER
- SMTP_PASSWORD

## 选填
- EMAIL_FROM           # 不填时默认等于 SMTP_USER
- EMAIL_SUBJECT_PREFIX # 例如 [ThreeBar]
- SCAN_SCRIPT_PATH     # 默认 scan_strategy.py
- CODE_FILE            # 默认 data/a_share_codes_for_akshare.csv
- BELOW_8B_FILE        # 默认 data/a_share_below_8b.csv
- ST_FILE              # 默认 data/st_stocks.csv
- START_DATE           # 默认保留脚本原值
- MAX_WORKERS          # 默认保留脚本原值
- BATCH_START          # 默认保留脚本原值
- BATCH_SIZE           # 默认保留脚本原值
- TEST_LIMIT           # 默认空
