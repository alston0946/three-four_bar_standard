# GitHub 每天下午 5 点自动跑脚本并发邮件

这套模板的目标是：
- 每个工作日新加坡时间下午 5:07 自动运行
- 运行你的扫描脚本
- 把结果 CSV 发到你的邮箱
- 同时把结果保存为 GitHub Actions artifact

## 你需要放进仓库的文件

- `scan_strategy.py`：你的策略脚本
- `data/a_share_codes_for_akshare.csv`
- `data/a_share_below_8b.csv`
- `data/st_stocks.csv`
- `requirements.txt`
- `automation/github_entry.py`
- `automation/send_email.py`
- `.github/workflows/daily_scan.yml`

## 第一步：把你的脚本接进来

最简单的做法：
1. 把你现在本地能跑的脚本重命名为 `scan_strategy.py`
2. 覆盖仓库根目录里的同名占位文件

这个包装器默认会覆盖这些全局变量：
- `TUSHARE_TOKEN`
- `TARGET_DATES`
- `END_DATE`
- `OUTPUT_FILE`
- `DEBUG_FILE`
- `FAILED_FILE`
- `FILTERED_FILE`
- `CODE_FILE`
- `BELOW_8B_FILE`
- `ST_FILE`

如果你的脚本变量名和这些一致，基本不用再改。

## 第二步：把三份基础数据放到 data 目录

默认路径：
- `data/a_share_codes_for_akshare.csv`
- `data/a_share_below_8b.csv`
- `data/st_stocks.csv`

如果你想用别的路径，也可以在 GitHub Secrets 里设置：
- `CODE_FILE`
- `BELOW_8B_FILE`
- `ST_FILE`

## 第三步：配置 GitHub Secrets

仓库 Settings -> Secrets and variables -> Actions

至少添加：
- `TUSHARE_TOKEN`
- `EMAIL_TO`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`

常见 Gmail 配置：
- `SMTP_HOST = smtp.gmail.com`
- `SMTP_PORT = 587`
- `SMTP_USER = 你的 Gmail`
- `SMTP_PASSWORD = 你的 App Password`
- `EMAIL_TO = 你的收件邮箱`
- `EMAIL_FROM = 你的 Gmail`（可选）

## 第四步：手动跑一次测试

进入仓库的 Actions 页，手动运行 `Daily ThreeBar Scan`。

你应该检查三件事：
1. 是否成功跑完
2. 是否成功收到邮件
3. artifact 里是否有 `outputs/` 目录结果

## 第五步：定时运行

工作流已经设置为：
- 每个工作日
- 新加坡时间 17:07

如果你要改时间，修改：
- `.github/workflows/daily_scan.yml`

## 邮件失败时优先检查

1. SMTP 用户名/密码是否正确
2. Gmail 是否用了 App Password
3. `EMAIL_TO` 是否正确
4. 你的脚本是否因为本地 Windows 路径残留而失败
5. 三份 data CSV 是否已提交到仓库

## 建议

- 第一次先用 `workflow_dispatch` 手动测试
- 跑通后再依赖定时任务
- 结果 CSV 建议只看邮件摘要，详细内容去 artifact 下载
