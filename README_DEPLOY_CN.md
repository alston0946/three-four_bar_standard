# GitHub 每天下午 5:07（新加坡时间）自动跑策略并发邮件

这个仓库已经内置了**真实可运行**的策略脚本 `scan_strategy.py`，不是空占位文件。

## 你还需要自己补的内容
1. 把下面三份 CSV 上传到 `data/` 目录：
   - `data/a_share_codes_for_akshare.csv`
   - `data/a_share_below_8b.csv`
   - `data/st_stocks.csv`
2. 在 GitHub 仓库里配置 Secrets：
   - `TUSHARE_TOKEN`
   - `EMAIL_TO`
   - `SMTP_HOST`
   - `SMTP_PORT`
   - `SMTP_USER`
   - `SMTP_PASSWORD`
3. 手动运行一次 workflow，确认能收到邮件。

## 目录说明
- `scan_strategy.py`：你的最终版扫描脚本，已改成 GitHub 可运行。
- `automation/github_entry.py`：GitHub 入口，负责设置 target_date、输出目录、发邮件。
- `automation/send_email.py`：SMTP 发信。
- `.github/workflows/daily_scan.yml`：自动化工作流。
- `outputs/`：运行结果会保存在这里，并上传为 artifact。

## 工作流时间
当前 cron 写的是：
- `7 9 * * 1-5`

GitHub Actions 默认按 UTC 解释，所以等于：
- **工作日 09:07 UTC**
- **新加坡时间 17:07**

## 第一次跑建议
1. 先上传 CSV 到 `data/`
2. 配好 Secrets
3. 进入 Actions 页面
4. 手动运行 `Daily ThreeBar Scan`
5. 看日志、看邮件、看 artifact

## 如果你想保留自己的脚本文件名
也可以把脚本放成别的文件名，比如：
- `my_strategy.py`

然后在 GitHub Secrets 里加：
- `SCAN_SCRIPT_PATH = my_strategy.py`

## Gmail 常见配置
- SMTP_HOST = `smtp.gmail.com`
- SMTP_PORT = `587`
- SMTP_USER = 你的 Gmail 地址
- SMTP_PASSWORD = 你的 App Password

注意：Gmail 这里不要填普通登录密码，要填 **App Password**。
