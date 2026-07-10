from __future__ import annotations
from typing import Optional
from odoo import api, models
from odoo.addons.jabin_core import JabinLogger
_logger = JabinLogger.get('auth.password_service')
_CRYPT_CONTEXT = None

def _get_crypt_context():
    global _CRYPT_CONTEXT
    if _CRYPT_CONTEXT is None:
        from passlib.context import CryptContext
        _CRYPT_CONTEXT = CryptContext(schemes=['bcrypt', 'pbkdf2_sha512'], default='bcrypt', deprecated=['pbkdf2_sha512'], bcrypt__rounds=12)
    return _CRYPT_CONTEXT

class PasswordService(models.AbstractModel):
    _name = 'jabin.password.service'
    _description = 'JABIN Password Service'

    @staticmethod
    def hash_password(plain: str) -> str:
        if not plain:
            raise ValueError('Cannot hash an empty password.')
        ctx = _get_crypt_context()
        return ctx.hash(plain)

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        if not plain or not hashed:
            return False
        try:
            ctx = _get_crypt_context()
            return ctx.verify(plain, hashed)
        except Exception:
            _logger.warning('Password verification error (malformed hash?)')
            return False

    @staticmethod
    def needs_rehash(hashed: str) -> bool:
        if not hashed:
            return False
        try:
            ctx = _get_crypt_context()
            return ctx.needs_update(hashed)
        except Exception:
            return False

    @api.model
    def set_user_password(self, user_id: int, plain: str) -> None:
        user = self.env['jabin.user'].browse(user_id)
        if not user.exists():
            return
        user.write({'password': plain})
        try:
            self.env['jabin.refresh.token'].revoke_all_for_user(user_id)
        except Exception:
            pass
        _logger.audit('Password changed for user %s', user_id, extra={'user_id': user_id, 'action': 'password_change'})

    @api.model
    def authenticate(self, login: str, plain_password: str) -> Optional[int]:
        if not login or not plain_password:
            return None
        User = self.env['jabin.user']
        user = User.find_by_login(login)
        if not user:
            user = User.find_by_phone(login)
        if not user:
            return None
        status = getattr(user, 'x_status', None)
        if status in ('suspended', 'inactive'):
            _logger.audit('Login blocked (suspended/inactive): user=%s', user.id, extra={'user_id': user.id, 'action': 'login_blocked_status'})
            return None
        try:
            from odoo.exceptions import AccessDenied
            user.with_user(user)._check_credentials(plain_password, {'interactive': True})
        except AccessDenied:
            return None
        except Exception:
            try:
                self.env.cr.execute("SELECT COALESCE(password, '') FROM res_users WHERE id=%s", [user.id])
                hashed = self.env.cr.fetchone()[0]
                if not hashed or not self.verify_password(plain_password, hashed):
                    return None
            except Exception:
                return None
        return user.id