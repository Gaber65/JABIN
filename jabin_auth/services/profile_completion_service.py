from __future__ import annotations
from typing import Any, Dict, List, Optional, Set
from odoo import api, models
from odoo.exceptions import ValidationError
from odoo.addons.jabin_core import JabinLogger



def _get_logger():
    global _logger
    if _logger is None:
        from odoo.addons.jabin_core import JabinLogger
        _logger = JabinLogger.get('profile_completion.service')
    return _logger


class ProfileCompletionService(models.AbstractModel):
    """JABIN Profile Completion Service.

    Validates that user profiles have required information for specific actions.
    This allows for progressive profile completion - users can register with
    just an email, and provide additional information only when needed.
    """
    _name = 'jabin.profile.completion.service'
    _description = 'JABIN Profile Completion Service'

    # -- Action Requirements Configuration -------------------------------- #
    # Define which fields are required for which actions
    ACTION_REQUIREMENTS: Dict[str, Set[str]] = {
        'create_order': {'name', 'phone'},
        'checkout': {'name', 'phone'},
        'edit_profile': set(),  # No requirements for editing profile
        'view_profile': set(),
        'create_address': {'name', 'phone'},
        'update_payment': {'name', 'phone'},
        'contact_support': {'name'},
        'apply_for_job': {'name', 'phone'},
        'default': set(),  # Default action has no requirements
    }

    # Field groups for validation messages
    FIELD_GROUPS: Dict[str, str] = {
        'name': 'Full Name',
        'phone': 'Phone Number',
        'email': 'Email Address',
        'x_phone': 'Phone Number',
        'x_avatar': 'Profile Picture',
    }

    # -- Validation Methods -------------------------------------------------- #
    @api.model
    def check_requirements(
            self,
            user_id: int,
            action: str,
            raise_exception: bool = False
    ) -> Dict[str, Any]:
        """Check if a user meets the profile requirements for an action.

        Args:
            user_id: The user ID to check
            action: The action being performed (e.g., 'create_order', 'checkout')
            raise_exception: If True, raise ValidationError instead of returning result

        Returns:
            Dictionary with:
            - 'valid': bool - whether requirements are met
            - 'missing_fields': List[str] - list of missing required fields
            - 'profile_completed': bool - whether profile is fully completed
            - 'required_fields': List[str] - all required fields for this action
        """
        if not user_id:
            if raise_exception:
                raise ValidationError('User ID is required.')
            return {
                'valid': False,
                'missing_fields': ['user_id'],
                'profile_completed': False,
                'required_fields': []
            }

        # Get user
        User = self.env['res.users']
        user = User.browse(user_id)

        if not user.exists():
            if raise_exception:
                raise ValidationError('User not found.')
            return {
                'valid': False,
                'missing_fields': ['user'],
                'profile_completed': False,
                'required_fields': []
            }

        # Get requirements for action
        required_fields = self.ACTION_REQUIREMENTS.get(action, self.ACTION_REQUIREMENTS['default'])

        # Check which fields are missing
        missing_fields = []
        for field in required_fields:
            if not self._has_field_value(user, field):
                missing_fields.append(field)

        # Check if profile is fully completed
        profile_completed = self.is_profile_completed(user_id)

        result = {
            'valid': len(missing_fields) == 0,
            'missing_fields': missing_fields,
            'profile_completed': profile_completed,
            'required_fields': list(required_fields)
        }

        if raise_exception and not result['valid']:
            field_names = [self.FIELD_GROUPS.get(f, f) for f in missing_fields]
            raise ValidationError(
                f"The following information is required to {action.replace('_', ' ')}: {', '.join(field_names)}"
            )

        return result

    @api.model
    def _has_field_value(self, user: 'res.users', field: str) -> bool:
        """Check if a user has a value for a specific field."""
        try:
            value = getattr(user, field, None)
            if value is None:
                return False
            if isinstance(value, str) and not value.strip():
                return False
            return True
        except Exception:
            return False

    @api.model
    def is_profile_completed(self, user_id: int) -> bool:
        """Check if a user's profile is fully completed.

        A profile is considered completed if all optional fields have values.
        """
        if not user_id:
            return False

        User = self.env['res.users']
        user = User.browse(user_id)

        if not user.exists():
            return False

        # Check all optional profile fields
        optional_fields = ['name', 'x_phone', 'x_avatar']

        for field in optional_fields:
            if not self._has_field_value(user, field):
                return False

        return True

    @api.model
    def get_missing_fields(self, user_id: int) -> List[str]:
        """Get a list of missing profile fields for a user."""
        if not user_id:
            return []

        User = self.env['res.users']
        user = User.browse(user_id)

        if not user.exists():
            return []

        missing = []
        optional_fields = ['name', 'x_phone', 'x_avatar']

        for field in optional_fields:
            if not self._has_field_value(user, field):
                missing.append(field)

        return missing

    @api.model
    def get_profile_status(self, user_id: int) -> Dict[str, Any]:
        """Get the complete profile completion status for a user.

        Returns a dictionary with detailed profile information.
        """
        if not user_id:
            return {
                'user_id': None,
                'profile_completed': False,
                'missing_fields': [],
                'completed_fields': [],
                'completion_percentage': 0
            }

        User = self.env['res.users']
        user = User.browse(user_id)

        if not user.exists():
            return {
                'user_id': user_id,
                'profile_completed': False,
                'missing_fields': [],
                'completed_fields': [],
                'completion_percentage': 0
            }

        # Define all profile fields
        all_fields = ['name', 'x_phone', 'x_avatar']
        total_fields = len(all_fields)

        missing = []
        completed = []

        for field in all_fields:
            if self._has_field_value(user, field):
                completed.append(field)
            else:
                missing.append(field)

        profile_completed = len(missing) == 0
        completion_percentage = int((len(completed) / total_fields) * 100) if total_fields > 0 else 0

        return {
            'user_id': user_id,
            'profile_completed': profile_completed,
            'missing_fields': missing,
            'completed_fields': completed,
            'completion_percentage': completion_percentage,
            'field_details': self._get_field_details(user)
        }

    @api.model
    def _get_field_details(self, user: 'res.users') -> Dict[str, Any]:
        """Get detailed information about each profile field."""
        details = {}

        fields_to_check = [
            ('name', 'Full Name', 'text'),
            ('x_phone', 'Phone Number', 'phone'),
            ('x_avatar', 'Profile Picture', 'image'),
        ]

        for field_name, display_name, field_type in fields_to_check:
            has_value = self._has_field_value(user, field_name)
            value = None
            try:
                value = getattr(user, field_name, None)
                if field_name == 'x_avatar' and value:
                    value = "[Image]"
            except Exception:
                value = None

            details[field_name] = {
                'display_name': display_name,
                'type': field_type,
                'has_value': has_value,
                'value': value,
                'required_for': self._get_required_actions(field_name)
            }

        return details

    @api.model
    def _get_required_actions(self, field: str) -> List[str]:
        """Get list of actions that require a specific field."""
        required_actions = []
        for action, fields in self.ACTION_REQUIREMENTS.items():
            if field in fields:
                required_actions.append(action)
        return required_actions

    # -- Action Validation Decorator ---------------------------------------- #
    @api.model
    def validate_action(self, action: str, user_id: int) -> None:
        """Validate that a user can perform an action.

        Raises ValidationError if requirements are not met.
        """
        self.check_requirements(user_id, action, raise_exception=True)

    # -- Profile Completion Methods ------------------------------------------ #
    @api.model
    def mark_profile_completed(self, user_id: int) -> bool:
        """Mark a user's profile as completed.

        This is called after all required fields are filled.
        """
        if not user_id:
            return False

        User = self.env['res.users']
        user = User.browse(user_id)

        if not user.exists():
            return False

        if self.is_profile_completed(user_id):
            try:
                user.write({'x_profile_completed': True})
                _get_logger().audit(
                    'Profile marked as completed: user=%s',
                    user_id,
                    extra={'user_id': user_id}
                )
                return True
            except Exception as exc:
                _get_logger().error('Failed to mark profile as completed: %s', exc)
                return False

        return False

    @api.model
    def get_next_required_action(self, user_id: int) -> Optional[str]:
        """Get the next action that requires profile completion.

        Returns the first action (by priority) that the user cannot perform
        due to missing profile information.
        """
        if not user_id:
            return None

        # Priority order for actions
        action_priority = [
            'create_order',
            'checkout',
            'create_address',
            'update_payment',
            'contact_support',
            'apply_for_job',
        ]

        for action in action_priority:
            result = self.check_requirements(user_id, action)
            if not result['valid']:
                return action

        return None