from __future__ import annotations

import mimetypes
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable


def send_email(subject: str, body: str, attachments: Iterable[Path] | None = None) -> None:
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]
    sender = os.environ.get("EMAIL_FROM", user)
    to_addr = os.environ["EMAIL_TO"]

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_addr
    msg.set_content(body)

    for path in attachments or []:
        path = Path(path)
        if not path.exists() or not path.is_file():
            continue
        ctype, _ = mimetypes.guess_type(path.name)
        if ctype is None:
            maintype, subtype = "application", "octet-stream"
        else:
            maintype, subtype = ctype.split("/", 1)
        with path.open("rb") as f:
            msg.add_attachment(f.read(), maintype=maintype, subtype=subtype, filename=path.name)

    with smtplib.SMTP(host, port, timeout=60) as server:
        server.ehlo()
        if port == 587:
            server.starttls()
            server.ehlo()
        server.login(user, password)
        server.send_message(msg)
