import os, resend, random
from utility.config import Static
from time import time

def send_light_email(to_email: str, endpoint: str, expiry: int, username: str) -> None:
    api_key = os.getenv("RESEND_API_KEY")
    resend.api_key = api_key
    resend.Emails.send({
        "from": "STREAK & DISCIPLINE <noreply@resend.dev>",
        "to": [to_email],
        "subject": "Password Reset Link — STREAK & DISCIPLINE",
        "html": """
        <div style="max-width:500px;margin:0 auto;font-family:system-ui,-apple-system,sans-serif;background:#fff;border-radius:12px;overflow:hidden;border:1px solid #e2e8f0">
            <table style="width:100%;padding:24px">
                <tr>
                    <td style="width:48px;vertical-align:top;padding-right:16px">
                        <img src="{logo_url}" alt="S&D" style="width:40px;height:40px;border-radius:8px">
                    </td>
                    <td style="vertical-align:top">
                        <p style="margin:0 0 2px;font-weight:700;font-size:16px;color:#0f172a">STREAK & DISCIPLINE</p>
                        <p style="margin:0;font-size:13px;color:#64748b">Password Reset</p>
                    </td>
                </tr>
            </table>
            <div style="padding:0 24px 20px">
                <p style="margin:0 0 12px;font-size:14px;color:#334155;line-height:1.6">Hello <strong>{username}</strong>, we received a request to reset the password for your account.</p>
                <a href="{link}" style="display:inline-block;padding:12px 28px;background:#2563eb;color:#fff;text-decoration:none;border-radius:8px;font-weight:600;font-size:14px;margin-bottom:16px">Reset My Password</a>
                <p style="margin:0 0 10px;font-size:12px;color:#64748b;line-height:1.5">This link takes you to a secure page where you can choose a new password. It expires in <strong>{expiry} minutes</strong> and can only be used once. scrunity: {identifier_to_make_each_email_unique}</p>
                <div style="background:#fff7ed;border:1px solid #fed7aa;padding:10px 12px;border-radius:6px;margin-bottom:14px">
                    <p style="margin:0;font-size:11px;color:#9a3412;line-height:1.5"><strong>&#9888; Don't share this link.</strong> Nobody from STREAK & DISCIPLINE will ever ask for it. If you didn't request this, ignore this email — your account is safe.</p>
                </div>
            </div>
            <div style="background:#f8fafc;padding:12px 24px;border-top:1px solid #e2e8f0;text-align:center">
                <p style="margin:0;font-size:11px;color:#94a3b8">Need help? <a href="mailto:issaabdulsalamope11@gmail.com" style="color:#2563eb">support@streakanddiscipline.com</a></p>
            </div>
        </div>
        """.format(link=Static.custom_base_url() + endpoint, expiry=int(expiry/60), username=username, logo_url=Static.logo_url(), identifier_to_make_each_email_unique = "".join(random.sample("{username}{link}{time}", 8)))})