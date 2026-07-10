from __future__ import annotations
from typing import Any, Dict, Optional, Tuple
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.addons.jabin_core import JabinLogger
from odoo.addons.jabin_security.utils.jwt_utils import DEFAULT_ACCESS_TTL, DEFAULT_REFRESH_TTL, JWTError, JWTUtils
_logger = JabinLogger.get('auth.token_service')

class TokenService(models.AbstractModel):
    _name = 'jabin.token.service'
    _description = 'JABIN Token Service'

    @staticmethod
    def _request_meta() -> Dict[str, str]:
        meta = {'ip_address': '', 'user_agent': ''}
        try:
            from odoo.http import request
            httprequest = request.httprequest
            forwarded = httprequest.headers.get('X-Forwarded-For')
            meta['ip_address'] = forwarded.split(',')[0].strip() if forwarded else httprequest.remote_addr or ''
            ua = httprequest.headers.get('User-Agent', '')
            meta['user_agent'] = ua[:256]
        except Exception:
            pass
        return meta

    @api.model
    def issue_pair(self, user_id: int, user_type: str, email: str) -> Dict[str, Any]:
        access_token = JWTUtils.encode_access_token(user_id, user_type, email)
        refresh_token = JWTUtils.encode_refresh_token(user_id, user_type, email)
        try:
            refresh_claims = JWTUtils.decode_token(refresh_token)
            jti = JWTUtils.get_token_id(refresh_claims)
            exp = refresh_claims.get('exp')
        except JWTError:
            raise ValidationError('Failed to issue refresh token.')
        import datetime as _dt
        if exp:
            expires_at = _dt.datetime.fromtimestamp(exp, tz=_dt.timezone.utc).replace(tzinfo=None)
        else:
            expires_at = fields.Datetime.now() + _dt.timedelta(seconds=DEFAULT_REFRESH_TTL)
        meta = self._request_meta()
        self.env['jabin.refresh.token'].register(jti=jti, user_id=user_id, expires_at=expires_at, ip_address=meta['ip_address'], user_agent=meta['user_agent'])
        _logger.audit('Token pair issued: user=%s', user_id, extra={'user_id': user_id, 'action': 'token_issued', 'jti': jti})
        return {'access_token': access_token, 'refresh_token': refresh_token, 'token_type': 'Bearer', 'expires_in': DEFAULT_ACCESS_TTL, 'refresh_expires_in': DEFAULT_REFRESH_TTL}

    @api.model
    def verify_access_token(self, token: str) -> Dict[str, Any]:
        claims = JWTUtils.decode_token(token)
        kind = JWTUtils.get_token_kind(claims)
        if kind != 'access':
            raise JWTError('Token is not an access token.')
        return claims

    @api.model
    def refresh(self, refresh_token: str) -> Dict[str, Any]:
        if not refresh_token:
            raise JWTError('Refresh token is required.')
        try:
            claims = JWTUtils.decode_token(refresh_token)
        except JWTError as exc:
            _logger.audit('Refresh failed (invalid token): %s', exc, extra={'action': 'refresh_invalid'})
            raise
        kind = JWTUtils.get_token_kind(claims)
        if kind != 'refresh':
            raise JWTError('Provided token is not a refresh token.')
        jti = JWTUtils.get_token_id(claims)
        user_id = JWTUtils.get_user_id(claims)
        if not jti or user_id is None:
            raise JWTError('Refresh token is missing required claims.')
        RefreshToken = self.env['jabin.refresh.token']
        token_row = RefreshToken.find_by_jti(jti)
        if not token_row:
            _logger.audit('Refresh failed (unknown jti): user=%s', user_id, extra={'user_id': user_id, 'action': 'refresh_unknown_jti', 'jti': jti})
            RefreshToken.revoke_all_for_user(user_id)
            raise JWTError('Refresh token is invalid.')
        if token_row.is_revoked:
            _logger.audit('Refresh REUSE detected: user=%s jti=%s', user_id, jti, extra={'user_id': user_id, 'action': 'refresh_reuse', 'jti': jti})
            RefreshToken.revoke_all_for_user(user_id)
            raise JWTError('Refresh token has been revoked. All sessions terminated for security.')
        token_row.revoke()
        user = self.env['res.users'].browse(user_id)
        if not user.exists():
            raise JWTError('User no longer exists.')
        user_type = getattr(user, 'x_user_type', None) or 'customer'
        email = user.login or ''
        try:
            self.env['jabin.audit.service'].log_token_refresh(user_id, old_jti=jti)
        except Exception:
            pass
        return self.issue_pair(user_id, user_type, email)

    @api.model
    def revoke_refresh_token(self, refresh_token: str) -> bool:
        if not refresh_token:
            return False
        try:
            claims = JWTUtils.decode_without_verification(refresh_token)
        except JWTError:
            return False
        jti = JWTUtils.get_token_id(claims)
        if not jti:
            return False
        token_row = self.env['jabin.refresh.token'].find_by_jti(jti)
        if not token_row:
            return False
        token_row.revoke()
        return True

    @api.model
    def revoke_all_for_user(self, user_id: int) -> int:
        return self.env['jabin.refresh.token'].revoke_all_for_user(user_id)