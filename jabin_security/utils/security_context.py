from __future__ import annotations
from typing import Any, Dict, List, Optional
_CTX_KEY: str = 'jabin_security_ctx'

class SecurityContext:
    __slots__ = ('user_id', 'user_type', 'email', 'roles', 'permissions', 'token_id', 'is_authenticated', 'is_admin')

    def __init__(self, *, user_id: Optional[int]=None, user_type: Optional[str]=None, email: Optional[str]=None, roles: Optional[List[str]]=None, permissions: Optional[set]=None, token_id: Optional[str]=None) -> None:
        self.user_id: Optional[int] = user_id
        self.user_type: Optional[str] = user_type
        self.email: Optional[str] = email
        self.roles: List[str] = list(roles) if roles else []
        self.permissions: set = set(permissions) if permissions else set()
        self.token_id: Optional[str] = token_id
        self.is_authenticated: bool = user_id is not None
        self.is_admin: bool = user_type == 'admin'

    def has_permission(self, code: str) -> bool:
        if self.is_admin:
            return True
        return code in self.permissions

    def has_any_permission(self, codes: List[str]) -> bool:
        if self.is_admin:
            return True
        return any((c in self.permissions for c in codes))

    def has_all_permissions(self, codes: List[str]) -> bool:
        if self.is_admin:
            return True
        return all((c in self.permissions for c in codes))

    def has_role(self, role_code: str) -> bool:
        return role_code in self.roles

    def to_dict(self) -> Dict[str, Any]:
        return {'user_id': self.user_id, 'user_type': self.user_type, 'email': self.email, 'roles': list(self.roles), 'permission_count': len(self.permissions), 'token_id': self.token_id, 'is_authenticated': self.is_authenticated, 'is_admin': self.is_admin}

    def __repr__(self) -> str:
        return f'SecurityContext(user_id={self.user_id}, user_type={self.user_type!r}, is_admin={self.is_admin}, roles={self.roles}, permissions={len(self.permissions)})'

    @classmethod
    def anonymous(cls) -> 'SecurityContext':
        return cls()

    @classmethod
    def set(cls, ctx: 'SecurityContext') -> None:
        try:
            from odoo.http import request
            request.env.context = {**request.env.context, _CTX_KEY: ctx}
        except Exception:
            pass

    @classmethod
    def get(cls) -> 'SecurityContext':
        try:
            from odoo.http import request
            ctx = request.env.context.get(_CTX_KEY)
            if ctx is not None:
                return ctx
        except Exception:
            pass
        return cls.anonymous()