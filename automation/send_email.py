# -*- coding: utf-8 -*-

import os
import smtplib
from pathlib import Path
from email.message import EmailMessage


def _get_env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _get_recipients() -> list:
    """
    优先读取 EMAIL_TO；
    兼容旧变量 MAIL_TO。
    多个邮箱可以用英文逗号分隔。
    """
    raw = _get_env("EMAIL_TO") or _get_env("MAIL_TO")

    if not raw:
        raise RuntimeError("未配置收件人邮箱：请设置 EMAIL_TO")

    recipients = []
    for item in raw.replace(";", ",").split(","):
        email = item.strip()
        if email:
            recipients.append(email)

    if not recipients:
        raise RuntimeError("EMAIL_TO 为空，无法发送邮件")

    return recipients


def _get_smtp_config():
    smtp_host = _get_env("SMTP_HOST")
    smtp_port_raw = _get_env("SMTP_PORT", "465")
    smtp_user = _get_env("SMTP_USER")

    # 兼容 SMTP_PASS / SMTP_PASSWORD
    smtp_pass = _get_env("SMTP_PASS") or _get_env("SMTP_PASSWORD")

    if not smtp_host:
        raise RuntimeError("未配置 SMTP_HOST")

    if not smtp_port_raw:
        smtp_port_raw = "465"

    try:
        smtp_port = int(smtp_port_raw)
    except ValueError:
        raise RuntimeError(f"SMTP_PORT 格式错误: {smtp_port_raw}")

    if not smtp_user:
        raise RuntimeError("未配置 SMTP_USER")

    if not smtp_pass:
        raise RuntimeError("未配置 SMTP_PASS。注意：QQ邮箱这里应该填写 SMTP 授权码，不是QQ登录密码")

    return smtp_host, smtp_port, smtp_user, smtp_pass


def send_email(subject: str, body: str, attachments=None):
    """
    发送扫描结果邮件。

    GitHub Secrets 推荐：
    EMAIL_TO      收件邮箱
    SMTP_HOST     smtp.qq.com
    SMTP_PORT     465
    SMTP_USER     发件邮箱
    SMTP_PASS     邮箱SMTP授权码
    """

    if attachments is None:
        attachments = []

    smtp_host, smtp_port, smtp_user, smtp_pass = _get_smtp_config()
    recipients = _get_recipients()

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)

    valid_attachments = []

    for file_path in attachments:
        if not file_path:
            continue

        p = Path(file_path)

        if not p.exists() or not p.is_file():
            print(f"附件不存在，跳过: {p}")
            continue

        valid_attachments.append(p)

        with open(p, "rb") as f:
            data = f.read()

        msg.add_attachment(
            data,
            maintype="application",
            subtype="octet-stream",
            filename=p.name
        )

    print("=" * 80)
    print("准备发送邮件")
    print(f"SMTP_HOST: {smtp_host}")
    print(f"SMTP_PORT: {smtp_port}")
    print(f"SMTP_USER: {smtp_user}")
    print(f"EMAIL_TO: {recipients}")
    print(f"附件数量: {len(valid_attachments)}")
    for p in valid_attachments:
        print(f"附件: {p}")
    print("=" * 80)

    if smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
    else:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

    print("邮件发送成功")
