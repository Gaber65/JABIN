from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from odoo import api, models
from odoo.exceptions import ValidationError
from odoo.addons.jabin_core import JabinLogger



def _get_logger():
    global _logger
    if _logger is None:
        from odoo.addons.jabin_core import JabinLogger
        _logger = JabinLogger.get('email.service')
    return _logger


class EmailService(models.AbstractModel):
    """JABIN Email Service.

    Handles sending verification emails with OTP codes.
    Supports SMTP configuration and email templates.
    """
    _name = 'jabin.email.service'
    _description = 'JABIN Email Service'

    # -- Email Template Configuration --------------------------------------- #
    DEFAULT_TEMPLATES = {
        'register': {
            'subject': 'Your JABIN Registration Verification Code',
            'body_html': '''<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px; border-radius: 10px 10px 0 0; text-align: center; color: white;">
        <h1 style="margin: 0; font-size: 28px;">🔐 JABIN</h1>
        <p style="margin: 10px 0 0 0; font-size: 18px; opacity: 0.9;">Registration Verification</p>
    </div>
    <div style="background: #f8f9fa; padding: 40px; border-radius: 0 0 10px 10px;">
        <h2 style="color: #333; margin-top: 0;">Welcome to JABIN!</h2>
        <p style="color: #666; line-height: 1.6;">
            Your registration verification code is:
        </p>
        <div style="background: white; border: 2px solid #667eea; border-radius: 8px; padding: 20px; text-align: center; margin: 30px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <span style="font-size: 48px; font-weight: bold; letter-spacing: 8px; color: #667eea;">{code}</span>
        </div>
        <p style="color: #666; line-height: 1.6;">
            This code will expire in <strong>5 minutes</strong>. Please enter it in the registration form to verify your account.
        </p>
        <p style="color: #666; line-height: 1.6;">
            If you didn't request this code, please ignore this email or contact support.
        </p>
        <p style="color: #999; font-size: 12px; margin-top: 40px;">
            © 2026 JABIN ERP. All rights reserved.
        </p>
    </div>
</div>''',
            'body_text': '''JABIN Registration Verification

Your registration verification code is: {code}

This code will expire in 5 minutes. Please enter it in the registration form to verify your account.

If you didn't request this code, please ignore this email or contact support.

© 2026 JABIN ERP. All rights reserved.'''
        },
        'login': {
            'subject': 'Your JABIN Login Verification Code',
            'body_html': '''<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px; border-radius: 10px 10px 0 0; text-align: center; color: white;">
        <h1 style="margin: 0; font-size: 28px;">🔐 JABIN</h1>
        <p style="margin: 10px 0 0 0; font-size: 18px; opacity: 0.9;">Login Verification</p>
    </div>
    <div style="background: #f8f9fa; padding: 40px; border-radius: 0 0 10px 10px;">
        <h2 style="color: #333; margin-top: 0;">Welcome Back!</h2>
        <p style="color: #666; line-height: 1.6;">
            Your login verification code is:
        </p>
        <div style="background: white; border: 2px solid #667eea; border-radius: 8px; padding: 20px; text-align: center; margin: 30px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <span style="font-size: 48px; font-weight: bold; letter-spacing: 8px; color: #667eea;">{code}</span>
        </div>
        <p style="color: #666; line-height: 1.6;">
            This code will expire in <strong>5 minutes</strong>. Please enter it in the login form to access your account.
        </p>
        <p style="color: #666; line-height: 1.6;">
            If you didn't request this code, please ignore this email or contact support.
        </p>
        <p style="color: #999; font-size: 12px; margin-top: 40px;">
            © 2026 JABIN ERP. All rights reserved.
        </p>
    </div>
</div>''',
            'body_text': '''JABIN Login Verification

Your login verification code is: {code}

This code will expire in 5 minutes. Please enter it in the login form to access your account.

If you didn't request this code, please ignore this email or contact support.

© 2026 JABIN ERP. All rights reserved.'''
        },
        'password_reset': {
            'subject': 'Your JABIN Password Reset Code',
            'body_html': '''<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 40px; border-radius: 10px 10px 0 0; text-align: center; color: white;">
        <h1 style="margin: 0; font-size: 28px;">🔐 JABIN</h1>
        <p style="margin: 10px 0 0 0; font-size: 18px; opacity: 0.9;">Password Reset</p>
    </div>
    <div style="background: #f8f9fa; padding: 40px; border-radius: 0 0 10px 10px;">
        <h2 style="color: #333; margin-top: 0;">Password Reset Request</h2>
        <p style="color: #666; line-height: 1.6;">
            Your password reset verification code is:
        </p>
        <div style="background: white; border: 2px solid #f5576c; border-radius: 8px; padding: 20px; text-align: center; margin: 30px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <span style="font-size: 48px; font-weight: bold; letter-spacing: 8px; color: #f5576c;">{code}</span>
        </div>
        <p style="color: #666; line-height: 1.6;">
            This code will expire in <strong>5 minutes</strong>.
        </p>
        <p style="color: #999; font-size: 12px; margin-top: 40px;">
            © 2026 JABIN ERP. All rights reserved.
        </p>
    </div>
</div>''',
            'body_text': '''JABIN Password Reset

Your password reset verification code is: {code}

This code will expire in 5 minutes.

© 2026 JABIN ERP. All rights reserved.'''
        }
    }

    # -- SMTP Configuration ------------------------------------------------ #
    @api.model
    def _get_smtp_config(self) -> dict:
        """Get SMTP configuration from system parameters."""
        try:
            from odoo.tools.config import config
            return {
                'smtp_server': config.get('smtp_server', 'localhost'),
                'smtp_port': int(config.get('smtp_port', 587)),
                'smtp_user': config.get('smtp_user', ''),
                'smtp_password': config.get('smtp_password', ''),
                'smtp_ssl': config.get('smtp_ssl', 'False').lower() == 'true',
                'smtp_tls': config.get('smtp_tls', 'True').lower() == 'true',
                'from_email': config.get('email_from', 'noreply@jabin.local'),
            }
        except Exception:
            return {
                'smtp_server': 'localhost',
                'smtp_port': 587,
                'smtp_user': '',
                'smtp_password': '',
                'smtp_ssl': False,
                'smtp_tls': True,
                'from_email': 'noreply@jabin.local',
            }

    # -- Email Sending ------------------------------------------------------- #
    @api.model
    def send_email(
            self,
            to: str,
            subject: str,
            body_html: Optional[str] = None,
            body_text: Optional[str] = None
    ) -> bool:
        """Send an email using Odoo's mail infrastructure.

        Args:
            to: Recipient email address
            subject: Email subject
            body_html: HTML body (optional)
            body_text: Plain text body (optional)

        Returns:
            True if email was sent successfully
        """
        if not to:
            raise ValidationError('Recipient email is required.')
        if not subject:
            raise ValidationError('Email subject is required.')

        try:
            Mail = self.env['mail.mail']

            mail_vals = {
                'subject': subject,
                'body_html': body_html,
                'body': body_text or body_html or '',
                'email_to': to,
                'email_from': self._get_smtp_config()['from_email'],
                'is_html': body_html is not None,
            }

            mail = Mail.create(mail_vals)
            mail.send()

            _get_logger().audit(
                'Email sent: to=%s subject=%s',
                to,
                subject[:50],
                extra={'to': to, 'subject': subject}
            )
            return True
        except Exception as exc:
            _get_logger().error('Failed to send email to %s: %s', to, exc)
            raise ValidationError(f'Failed to send email: {exc}')

    @api.model
    def send_verification_code(
            self,
            email: str,
            code: str,
            purpose: str = 'register'
    ) -> bool:
        """Send a verification code email.

        Args:
            email: Recipient email address
            code: The OTP code to send
            purpose: Purpose of the OTP (register, login, etc.)

        Returns:
            True if email was sent successfully
        """
        if not email:
            raise ValidationError('Email is required.')
        if not code:
            raise ValidationError('Verification code is required.')

        # Get template for purpose
        template_config = self.DEFAULT_TEMPLATES.get(purpose, self.DEFAULT_TEMPLATES['register'])

        subject = template_config['subject']
        body_html = template_config['body_html'].replace('{code}', code)
        body_text = template_config['body_text'].replace('{code}', code)

        return self.send_email(
            to=email,
            subject=subject,
            body_html=body_html,
            body_text=body_text
        )

    @api.model
    def send_welcome_email(self, email: str, name: Optional[str] = None) -> bool:
        """Send a welcome email after successful registration.

        Args:
            email: Recipient email address
            name: User's name (optional)

        Returns:
            True if email was sent successfully
        """
        greeting = f"Hello {name or 'User'}," if name else "Hello,"

        subject = "Welcome to JABIN!"
        body_html = f'''<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px; border-radius: 10px 10px 0 0; text-align: center; color: white;">
        <h1 style="margin: 0; font-size: 28px;">🔐 JABIN</h1>
    </div>
    <div style="background: #f8f9fa; padding: 40px; border-radius: 0 0 10px 10px;">
        <h2 style="color: #333; margin-top: 0;">Welcome to JABIN!</h2>
        <p style="color: #666; line-height: 1.6;">
            {greeting}
        </p>
        <p style="color: #666; line-height: 1.6;">
            Your account has been successfully created and verified. You can now log in using your email address and verification codes.
        </p>
        <p style="color: #666; line-height: 1.6;">
            <strong>Important:</strong> For security, we use passwordless authentication. You will receive a verification code via email each time you need to log in or perform sensitive actions.
        </p>
        <p style="color: #999; font-size: 12px; margin-top: 40px;">
            © 2026 JABIN ERP. All rights reserved.
        </p>
    </div>
</div>'''

        body_text = f'''Welcome to JABIN!

{greeting}

Your account has been successfully created and verified. You can now log in using your email address and verification codes.

Important: For security, we use passwordless authentication. You will receive a verification code via email each time you need to log in or perform sensitive actions.

© 2026 JABIN ERP. All rights reserved.'''

        return self.send_email(
            to=email,
            subject=subject,
            body_html=body_html,
            body_text=body_text
        )

    # -- Template Management ----------------------------------------------- #
    @api.model
    def get_template(self, purpose: str) -> dict:
        """Get the email template for a specific purpose."""
        return self.DEFAULT_TEMPLATES.get(purpose, self.DEFAULT_TEMPLATES['register'])

    @api.model
    def set_custom_template(self, purpose: str, subject: str, body_html: str, body_text: str) -> bool:
        """Set a custom email template for a specific purpose.

        This allows customization of email templates without modifying code.
        Templates are stored in system parameters.
        """
        try:
            Param = self.env['ir.config_parameter']

            # Store template in system parameters
            Param.set_param(f'jabin.email.template.{purpose}.subject', subject)
            Param.set_param(f'jabin.email.template.{purpose}.body_html', body_html)
            Param.set_param(f'jabin.email.template.{purpose}.body_text', body_text)

            return True
        except Exception as exc:
            _get_logger().error('Failed to set custom template: %s', exc)
            return False

    @api.model
    def get_custom_template(self, purpose: str) -> Optional[dict]:
        """Get a custom email template from system parameters."""
        try:
            Param = self.env['ir.config_parameter']

            subject = Param.get_param(f'jabin.email.template.{purpose}.subject')
            body_html = Param.get_param(f'jabin.email.template.{purpose}.body_html')
            body_text = Param.get_param(f'jabin.email.template.{purpose}.body_text')

            if subject and body_html:
                return {
                    'subject': subject,
                    'body_html': body_html,
                    'body_text': body_text
                }
        except Exception:
            pass

        return None