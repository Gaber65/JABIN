# addons/jabin_security/models/security_context.py
from odoo import models


class SecurityContext(models.AbstractModel):
    _name = 'jabin.security.context'
    _description = 'Security Context'

    def get_current_user(self):
        """
        Retrieve the currently authenticated user.
        Updated to lookup jabin.user instead of res.users.
        """
        # Assuming JWT middleware injects the user_id into the context
        user_id = self.env.context.get('jwt_user_id')
        if not user_id:
            return None

        # GREENFIELD CHANGE: Lookup jabin.user
        user = self.env['jabin.user'].browse(user_id).exists()
        return user if user else None