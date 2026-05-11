# GitHub Secrets 清单

在仓库 Settings -> Secrets and variables -> Actions 中添加：

## 必填
- TUSHARE_TOKEN
- EMAIL_TO
- SMTP_HOST
- SMTP_PORT
- SMTP_USER
- SMTP_PASSWORD

## 推荐
- EMAIL_FROM                 # 不填时默认等于 SMTP_USER
- EMAIL_SUBJECT_PREFIX       # 例如 [ThreeBar]
- SCAN_SCRIPT_PATH           # 默认 scan_strategy.py
- START_DATE                 # 例如 20250101
- MAX_WORKERS                # 默认 1
- BATCH_START                # 默认 0
- BATCH_SIZE                 # 默认 10000
- TEST_LIMIT                 # 调试时可填，如 50
- SLEEP_SEC                  # 默认 0.10

## 只有当你不把 CSV 放在默认 data/ 路径时才需要设置
- CODE_FILE
- BELOW_8B_FILE
- ST_FILE
