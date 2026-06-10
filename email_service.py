from html import escape
from typing import Optional

import httpx

from app_settings import get_settings


class EmailDeliveryError(RuntimeError):
    def __init__(self, message: str, phase: str, original: Optional[Exception] = None) -> None:
        super().__init__(message)
        self.phase = phase
        self.original = original


class EmailService:
    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def is_configured(self) -> bool:
        return self.settings.email_configured

    @property
    def config_errors(self) -> list:
        errors = []
        if not self.settings.email_api_url:
            errors.append("EMAIL_API_URL")
        if not self.settings.email_from:
            errors.append("EMAIL_FROM")
        if not self.settings.email_api_key:
            errors.append("EMAIL_API_KEY")
        return errors

    def check(self) -> bool:
        return self.is_configured

    def send_html(self, to_email: str, subject: str, html_body: str) -> None:
        if not self.is_configured:
            missing = ", ".join(self.config_errors) or "EMAIL_API settings"
            raise RuntimeError(f"Email API is not configured: {missing}")

        payload = {
            "from": self.settings.email_from,
            "to": [to_email],
            "subject": subject,
            "html": html_body,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.email_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            response = httpx.post(
                self.settings.email_api_url,
                headers=headers,
                json=payload,
                timeout=self.settings.email_api_timeout,
            )
        except Exception as exc:
            raise EmailDeliveryError(f"{type(exc).__name__}: {exc}", "connect", exc) from exc

        if response.status_code >= 400:
            detail = _extract_detail(response)
            raise EmailDeliveryError(
                f"Email API rejected the request: {response.status_code} {detail}",
                "send",
            )


def _extract_detail(response: httpx.Response) -> str:
    try:
        data = response.json()
    except Exception:
        return response.text.strip() or response.reason_phrase

    if isinstance(data, dict):
        for key in ("message", "error", "detail"):
            value = data.get(key)
            if value:
                return str(value)
    return str(data)


def reset_password_email(code: str) -> str:
    safe_code = escape(code)
    return f"""
    <html lang="ar" dir="rtl">
      <body style="font-family: Arial, sans-serif; line-height: 1.8;">
        <h2>استعادة كلمة المرور</h2>
        <p>مرحباً،</p>
        <p>تم طلب إعادة تعيين كلمة المرور الخاصة بحسابك.</p>
        <p>رمز التحقق:</p>
        <p style="font-size: 28px; font-weight: bold; letter-spacing: 4px;">{safe_code}</p>
        <p>صلاحية الرمز: 10 دقائق</p>
        <p>إذا لم تطلب ذلك تجاهل الرسالة.</p>
      </body>
    </html>
    """


def verification_email(code: str) -> str:
    safe_code = escape(code)
    return f"""
    <html lang="ar" dir="rtl">
      <body style="font-family: Arial, sans-serif; line-height: 1.8;">
        <h2>تفعيل البريد الإلكتروني</h2>
        <p>مرحباً،</p>
        <p>استخدم الرمز التالي لتفعيل حسابك:</p>
        <p style="font-size: 28px; font-weight: bold; letter-spacing: 4px;">{safe_code}</p>
        <p>صلاحية الرمز: 10 دقائق</p>
      </body>
    </html>
    """
