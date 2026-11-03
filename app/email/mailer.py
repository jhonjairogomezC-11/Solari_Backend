"""Envío de correo con backend conmutable por configuración.

MAIL_BACKEND=console  -> escribe el correo en el log (desarrollo, costo cero).
MAIL_BACKEND=smtp     -> envía por SMTP (buzón existente o proveedor transaccional).

La lógica de recuperación/verificación NO depende del proveedor concreto: solo
invoca send(). Cambiar de proveedor es cuestión de configuración.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import Settings

logger = logging.getLogger("solary.mail")


class Mailer:
    def __init__(self, settings: Settings):
        self.settings = settings

    def send(self, *, to: str, subject: str, body: str) -> None:
        backend = self.settings.mail_backend.lower()
        if backend == "smtp":
            self._send_smtp(to=to, subject=subject, body=body)
        else:
            # Desarrollo: no se envía nada real, se registra sin datos sensibles.
            logger.info("[MAIL:console] to=%s subject=%s", to, subject)
            logger.debug("[MAIL:console] body=%s", body)

    def _send_smtp(self, *, to: str, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["From"] = f"{self.settings.mail_from_name} <{self.settings.mail_from_address}>"
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)

        if self.settings.mail_use_tls:
            with smtplib.SMTP(self.settings.mail_host, self.settings.mail_port) as server:
                server.starttls()
                if self.settings.mail_username:
                    server.login(self.settings.mail_username, self.settings.mail_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(self.settings.mail_host, self.settings.mail_port) as server:
                if self.settings.mail_username:
                    server.login(self.settings.mail_username, self.settings.mail_password)
                server.send_message(msg)
