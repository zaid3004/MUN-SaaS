import os
import resend
from typing import Optional

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@munsaas.com")


def send_password_reset_email(to_email: str, reset_link: str) -> bool:
    """Send password reset email using Resend."""
    if not RESEND_API_KEY:
        print(f"⚠️  RESEND_API_KEY not set. Reset link: {reset_link}")
        return False

    resend.api_key = RESEND_API_KEY

    html_content = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 500px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 30px; border-radius: 12px;">
            <h1 style="color: #ffffff; font-size: 24px; margin: 0 0 20px 0;">Password Reset</h1>
            
            <p style="color: #a0a0b0; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                You requested to reset your MUN SaaS account password. Click the button below to create a new password. This link will expire in 24 hours.
            </p>
            
            <a href="{reset_link}" style="display: inline-block; background: #ff6f61; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; margin: 10px 0;">
                Reset Password
            </a>
            
            <p style="color: #606080; font-size: 14px; line-height: 1.6; margin: 20px 0 0 0;">
                If you didn't request this, you can safely ignore this email. Your password remains unchanged.
            </p>
        </div>
        
        <p style="color: #404060; font-size: 12px; text-align: center; margin-top: 20px;">
            MUN SaaS - Model United Nations Management Platform
        </p>
    </div>
    """

    try:
        r = resend.Emails.send(
            {
                "from": f"MUN SaaS <{DEFAULT_FROM_EMAIL}>",
                "to": to_email,
                "subject": "Reset your MUN SaaS password",
                "html": html_content,
            }
        )
        print(f"✅ Password reset email sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False
