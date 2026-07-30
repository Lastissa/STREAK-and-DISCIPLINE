import os, resend, random
from utility.config import Static
from time import time

def send_password_reset_email(to_email: str, endpoint: str, expiry: int, username: str) -> None:
    """Sends email with link for password reset."""
    
    api_key = os.getenv("RESEND_API_KEY")
    resend.api_key = api_key
    resend.Emails.send({
        "from": Static.official_email(),
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



def send_password_reset_successful_email(to_email: str, username: str) -> None:
    """Notify user that their password was successfully reset."""

    logo = Static.logo_url()
    login_link = Static.custom_base_url() + "/v1/login/"
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin:0;padding:0;background:#f1f5f9;font-family:system-ui,-apple-system,sans-serif">
        <table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:30px 0">
            <tr>
                <td align="center">
                    <table width="480" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;overflow:hidden;border:1px solid #e2e8f0">

                        <!-- Header with logo -->
                        <tr>
                            <td style="padding:20px 24px;border-bottom:1px solid #f1f5f9">
                                <table cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td style="padding-right:12px">
                                            <img src="{logo}" alt="S&D" width="40" height="40" style="border-radius:8px;display:block">
                                        </td>
                                        <td>
                                            <p style="margin:0;font-weight:700;font-size:16px;color:#0f172a">STREAK & DISCIPLINE</p>
                                            <p style="margin:4px 0 0;font-size:13px;color:#64748b">Security Notification</p>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <!-- Main content -->
                        <tr>
                            <td style="padding:24px">
                                
                                <!-- Success icon and heading -->
                                <table cellpadding="0" cellspacing="0" style="margin-bottom:16px">
                                    <tr>
                                        <td style="padding-right:10px">
                                            <span style="display:inline-block;width:36px;height:36px;background:#dcfce7;border-radius:50%;text-align:center;line-height:36px;font-size:18px"> </span>
                                        </td>
                                        <td>
                                            <h2 style="margin:0;font-size:18px;color:#0f172a;font-weight:700">Password Changed Successfully</h2>
                                        </td>
                                    </tr>
                                </table>

                                <!-- Greeting -->
                                <p style="margin:0 0 12px;font-size:14px;color:#334155;line-height:1.6">
                                    Hello <strong>{username}</strong>,
                                </p>

                                <!-- Main message -->
                                <p style="margin:0 0 20px;font-size:14px;color:#334155;line-height:1.6">
                                    The password for your STREAK & DISCIPLINE account was just changed. 
                                    If you made this change, you're all set — no further action is needed.
                                </p>

                                <!-- Sign-in button -->
                                <table cellpadding="0" cellspacing="0" style="margin-bottom:20px">
                                    <tr>
                                        <td align="center" style="background:#2563eb;border-radius:8px">
                                            <a href="{login_link}" style="display:inline-block;padding:12px 28px;color:#fff;text-decoration:none;font-weight:600;font-size:14px">Sign In to Your Account</a>
                                        </td>
                                    </tr>
                                </table>

                                <!-- Warning box -->
                                <table cellpadding="0" cellspacing="0" style="background:#fef2f2;border-left:3px solid #ef4444;border-radius:6px;margin-bottom:0">
                                    <tr>
                                        <td style="padding:12px 14px">
                                            <p style="margin:0;font-size:12px;color:#991b1b;line-height:1.5">
                                                <strong>Didn't make this change?</strong> Someone may have accessed your account. 
                                                Reset your password immediately and contact our support team. 
                                                We take account security seriously.
                                            </p>
                                        </td>
                                    </tr>
                                </table>

                            </td>
                        </tr>

                        <!-- Footer -->
                        <tr>
                            <td style="background:#f8fafc;padding:14px 24px;border-top:1px solid #e2e8f0;text-align:center">
                                <p style="margin:0 0 4px;font-size:11px;color:#94a3b8">
                                    This is an automated security notification from STREAK & DISCIPLINE.
                                </p>
                                <p style="margin:0;font-size:11px;color:#94a3b8">
                                    Need help? 
                                    <a href="mailto:issaabdulsalamope11@gmail.com" style="color:#2563eb;text-decoration:none">support@streakanddiscipline.com</a>
                                    &nbsp;·&nbsp;
                                    <a href="https://wa.me/2347013687825" style="color:#2563eb;text-decoration:none">WhatsApp Support</a>
                                </p>
                            </td>
                        </tr>

                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    resend.Emails.send({
        "from": Static.official_email(),
        "to": [to_email],
        "subject": "Password Changed — STREAK & DISCIPLINE",
        "html": html,
    })
    


def send_welcome_email(to_email: str, username: str) -> None:
    """Send a welcome email after successful onboarding."""
    
    logo = Static.logo_url()
    dashboard_link = Static.custom_base_url() + "/v1/dashboard/"
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin:0;padding:0;background:#f1f5f9;font-family:system-ui,-apple-system,sans-serif">
        <table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:30px 0">
            <tr>
                <td align="center">
                    <table width="480" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;overflow:hidden;border:1px solid #e2e8f0">
                        
                        <!-- Header -->
                        <tr>
                            <td style="padding:20px 24px;border-bottom:1px solid #f1f5f9">
                                <table cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td style="padding-right:12px">
                                            <img src="{logo}" alt="S&D" width="40" height="40" style="border-radius:8px;display:block">
                                        </td>
                                        <td>
                                            <p style="margin:0;font-weight:700;font-size:16px;color:#0f172a">STREAK & DISCIPLINE</p>
                                            <p style="margin:4px 0 0;font-size:13px;color:#64748b">Welcome to the journey</p>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        
                        <!-- Main content -->
                        <tr>
                            <td style="padding:24px">
                                <h2 style="margin:0 0 12px;font-size:20px;color:#0f172a;font-weight:700">
                                    Day 1 starts now, {username}
                                </h2>
                                
                                <p style="margin:0 0 16px;font-size:14px;color:#334155;line-height:1.6">
                                    Your commitment has been set, and your dashboard is ready. 
                                    Here's what to do next:
                                </p>
                                
                                <table cellpadding="0" cellspacing="0" style="margin-bottom:20px">
                                    <tr>
                                        <td style="padding:0 0 10px 0;font-size:14px;color:#334155">
                                            <span style="display:inline-block;width:24px;height:24px;background:#dbeafe;border-radius:50%;text-align:center;line-height:24px;font-size:12px;color:#2563eb;margin-right:8px">1</span>
                                            Bookmark your <a href="{dashboard_link}" style="color:#2563eb;text-decoration:none;font-weight:600">dashboard</a>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding:0 0 10px 0;font-size:14px;color:#334155">
                                            <span style="display:inline-block;width:24px;height:24px;background:#dbeafe;border-radius:50%;text-align:center;line-height:24px;font-size:12px;color:#2563eb;margin-right:8px">2</span>
                                            Do your first check-in tonight — answer one question honestly
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding:0 0 10px 0;font-size:14px;color:#334155">
                                            <span style="display:inline-block;width:24px;height:24px;background:#dbeafe;border-radius:50%;text-align:center;line-height:24px;font-size:12px;color:#2563eb;margin-right:8px">3</span>
                                            Watch your streak grow — one day at a time
                                        </td>
                                    </tr>
                                </table>
                                
                                <table cellpadding="0" cellspacing="0" style="margin-bottom:20px">
                                    <tr>
                                        <td align="center" style="background:#2563eb;border-radius:8px">
                                            <a href="{dashboard_link}" style="display:inline-block;padding:12px 28px;color:#fff;text-decoration:none;font-weight:600;font-size:14px">Go to Your Dashboard</a>
                                        </td>
                                    </tr>
                                </table>
                                
                                <div style="background:#fff7ed;border:1px solid #fed7aa;padding:10px 12px;border-radius:6px;margin-bottom:0">
                                    <p style="margin:0;font-size:12px;color:#9a3412;line-height:1.5">
                                        <strong>Pro tip:</strong> Your first week is free with all Pro features unlocked. 
                                        Set up reminders from your dashboard settings to never miss a check-in.
                                    </p>
                                </div>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="background:#f8fafc;padding:14px 24px;border-top:1px solid #e2e8f0;text-align:center">
                                <p style="margin:0;font-size:11px;color:#94a3b8">
                                    Need help? 
                                    <a href="mailto:issaabdulsalamope11@gmail.com" style="color:#2563eb;text-decoration:none">support@streakanddiscipline.com</a>
                                    &nbsp;·&nbsp;
                                    <a href="https://wa.me/2347013687825" style="color:#2563eb;text-decoration:none">WhatsApp</a>
                                </p>
                            </td>
                        </tr>
                        
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    resend.Emails.send({
        "from": Static.official_email(),
        "to": [to_email],
        "subject": "Welcome to STREAK & DISCIPLINE — Day 1 starts now",
        "html": html,
    })


def send_partner_request_notification(to_email: str, from_username: str, from_userid: str) -> None:
    """Notify a user that someone wants to be their accountability partner."""
    
    logo = Static.logo_url()
    dashboard_link = Static.custom_base_url() + "/v1/dashboard/"
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin:0;padding:0;background:#f1f5f9;font-family:system-ui,-apple-system,sans-serif">
        <table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:30px 0">
            <tr>
                <td align="center">
                    <table width="480" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;overflow:hidden;border:1px solid #e2e8f0">
                        
                        <!-- Header -->
                        <tr>
                            <td style="padding:20px 24px;border-bottom:1px solid #f1f5f9">
                                <table cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td style="padding-right:12px">
                                            <img src="{logo}" alt="S&D" width="40" height="40" style="border-radius:8px;display:block">
                                        </td>
                                        <td>
                                            <p style="margin:0;font-weight:700;font-size:16px;color:#0f172a">STREAK & DISCIPLINE</p>
                                            <p style="margin:4px 0 0;font-size:13px;color:#64748b">Partner Request</p>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        
                        <!-- Main content -->
                        <tr>
                            <td style="padding:24px">
                                <h2 style="margin:0 0 12px;font-size:18px;color:#0f172a;font-weight:700">
                                    {from_username} is giving you permission to see their discipline
                                </h2>
                                
                                <p style="margin:0 0 16px;font-size:14px;color:#334155;line-height:1.6">
                                    <strong>@{from_userid}</strong> has sent you a partner request. 
                                    <strong>If you accept, you will be able to see their:</strong>
                                </p>
                                
                                <div style="background:#f0f9ff;border:1px solid #bae6fd;padding:12px 14px;border-radius:8px;margin-bottom:20px">
                                    <p style="margin:0;font-size:13px;color:#0c4a6e;line-height:1.5">
                                        * Their current streak count across all commitments<br>
                                        * Their Zeal Score (discipline index)<br>
                                        * Their commitment names and categories<br>
                                    </p>
                                </div>
                                
                                <div style="background:#fff7ed;border:1px solid #fed7aa;padding:12px 14px;border-radius:8px;margin-bottom:20px">
                                    <p style="margin:0;font-size:13px;color:#9a3412;line-height:1.5">
                                        <strong>Important:</strong> This is a one-way permission. {from_username} is choosing to share their data with you. They will <strong>not</strong> be able to see your scores unless you also send them a partner request.
                                    </p>
                                </div>
                                
                                <table cellpadding="0" cellspacing="0" style="margin-bottom:20px">
                                    <tr>
                                        <td align="center" style="background:#2563eb;border-radius:8px">
                                            <a href="{dashboard_link}" style="display:inline-block;padding:12px 28px;color:#fff;text-decoration:none;font-weight:600;font-size:14px">View Request on Dashboard</a>
                                        </td>
                                    </tr>
                                </table>
                                
                                <p style="margin:0;font-size:12px;color:#64748b;line-height:1.5">
                                    You can accept or decline this request from your dashboard. 
                                    If you accept, you'll see {from_username}'s consistency data on your partners widget. 
                                    You can remove them anytime from Profile → Settings.
                                </p>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="background:#f8fafc;padding:14px 24px;border-top:1px solid #e2e8f0;text-align:center">
                                <p style="margin:0;font-size:11px;color:#94a3b8">
                                    This is an automated notification from STREAK & DISCIPLINE.
                                </p>
                                <p style="margin:4px 0 0;font-size:11px;color:#94a3b8">
                                    Need help? 
                                    <a href="mailto:issaabdulsalamope11@gmail.com" style="color:#2563eb;text-decoration:none">support@streakanddiscipline.com</a>
                                    &nbsp;·&nbsp;
                                    <a href="https://wa.me/2347013687825" style="color:#2563eb;text-decoration:none">WhatsApp</a>
                                </p>
                            </td>
                        </tr>
                        
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    resend.Emails.send({
        "from": Static.official_email(),
        "to": [to_email],
        "subject": f"{from_username} wants to be your accountability partner",
        "html": html,
    })