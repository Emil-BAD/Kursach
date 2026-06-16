from __future__ import annotations

from dataclasses import dataclass

from api.core.exceptions import ForbiddenError
from api.db.models import User


ADMIN_SHELL_ROLES = {"admin", "commandant", "council_president", "council_member"}

ROLE_PERMISSIONS = {
    "admin": {
        "can_access_admin_shell": True,
        "can_manage_users": True,
        "can_manage_residence": True,
        "can_manage_requests": True,
        "can_manage_payments": True,
        "can_manage_market": True,
        "can_manage_news": True,
        "can_manage_events": True,
        "can_manage_calendar": True,
        "can_manage_discipline": True,
        "can_manage_cleanliness": True,
        "can_view_reports": True,
        "can_send_notifications": True,
    },
    "commandant": {
        "can_access_admin_shell": True,
        "can_manage_users": True,
        "can_manage_residence": True,
        "can_manage_requests": True,
        "can_manage_payments": True,
        "can_manage_market": True,
        "can_manage_news": True,
        "can_manage_events": True,
        "can_manage_calendar": True,
        "can_manage_discipline": True,
        "can_manage_cleanliness": True,
        "can_view_reports": True,
        "can_send_notifications": True,
    },
    "council_president": {
        "can_access_admin_shell": True,
        "can_manage_users": False,
        "can_manage_residence": False,
        "can_manage_requests": False,
        "can_manage_payments": True,
        "can_manage_market": False,
        "can_manage_news": True,
        "can_manage_events": True,
        "can_manage_calendar": True,
        "can_manage_discipline": False,
        "can_manage_cleanliness": False,
        "can_view_reports": False,
        "can_send_notifications": True,
    },
    "council_member": {
        "can_access_admin_shell": True,
        "can_manage_users": False,
        "can_manage_residence": False,
        "can_manage_requests": False,
        "can_manage_payments": True,
        "can_manage_market": False,
        "can_manage_news": True,
        "can_manage_events": True,
        "can_manage_calendar": True,
        "can_manage_discipline": False,
        "can_manage_cleanliness": False,
        "can_view_reports": False,
        "can_send_notifications": True,
    },
}

MODULE_REGISTRY = (
    {"key": "users", "label": "Пользователи", "route": "/admin/users", "permission": "can_manage_users", "counter_key": None},
    {"key": "residence", "label": "Проживание", "route": "/admin/residence", "permission": "can_manage_residence", "counter_key": None},
    {"key": "service_requests", "label": "Заявки", "route": "/admin/requests", "permission": "can_manage_requests", "counter_key": "new_requests"},
    {"key": "payments", "label": "Оплаты", "route": "/admin/payments", "permission": "can_manage_payments", "counter_key": "overdue_invoices"},
    {"key": "market", "label": "Маркет", "route": "/admin/market", "permission": "can_manage_market", "counter_key": "products_on_moderation"},
    {"key": "news", "label": "Новости", "route": "/admin/news", "permission": "can_manage_news", "counter_key": None},
    {"key": "events", "label": "Мероприятия", "route": "/admin/events", "permission": "can_manage_events", "counter_key": None},
    {"key": "calendar", "label": "Календарь", "route": "/admin/calendar", "permission": "can_manage_calendar", "counter_key": "upcoming_calendar_events"},
    {"key": "discipline", "label": "Дисциплина", "route": "/admin/discipline", "permission": "can_manage_discipline", "counter_key": "new_violations"},
    {"key": "cleanliness", "label": "Чистота", "route": "/admin/cleanliness", "permission": "can_manage_cleanliness", "counter_key": "rooms_below_threshold"},
    {"key": "reports", "label": "Отчёты", "route": "/admin/reports", "permission": "can_view_reports", "counter_key": None},
    {"key": "notifications", "label": "Уведомления", "route": "/admin/notifications", "permission": "can_send_notifications", "counter_key": None},
)


@dataclass(slots=True)
class AdminScope:
    mode: str
    dormitory_id: int | None
    dormitory_name: str | None


class AdminPermissionsService:
    def role_name(self, user: User | None) -> str | None:
        if not user or not user.role:
            return None
        return user.role.role_name

    def ensure_admin_shell_access(self, user: User | None) -> None:
        if self.role_name(user) not in ADMIN_SHELL_ROLES:
            raise ForbiddenError("Этот раздел доступен только административным ролям")

    def permissions_for(self, user: User | None) -> dict[str, bool]:
        self.ensure_admin_shell_access(user)
        role_name = self.role_name(user)
        return dict(ROLE_PERMISSIONS.get(role_name or "", {}))

    def ensure_permission(self, user: User | None, permission_key: str) -> None:
        permissions = self.permissions_for(user)
        if not permissions.get(permission_key, False):
            raise ForbiddenError("Недостаточно прав для этого раздела админки")

    def scope_for(self, user: User, dormitory_id: int | None = None) -> AdminScope:
        self.ensure_admin_shell_access(user)
        if self.role_name(user) == "admin":
            dormitory_name = None
            if dormitory_id is not None and user.dormitory and user.dormitory.id == dormitory_id:
                dormitory_name = user.dormitory.name
            return AdminScope(mode="global", dormitory_id=dormitory_id, dormitory_name=dormitory_name)
        return AdminScope(
            mode="dormitory",
            dormitory_id=user.dormitory_id,
            dormitory_name=user.dormitory.name if user.dormitory else None,
        )

    def scoped_dormitory_id(self, user: User, dormitory_id: int | None = None) -> int | None:
        return self.scope_for(user, dormitory_id).dormitory_id

    def build_modules(self, user: User, counters: dict[str, int]) -> list[dict]:
        permissions = self.permissions_for(user)
        items: list[dict] = []
        for module in MODULE_REGISTRY:
            if not permissions.get(module["permission"], False):
                continue
            counter_key = module["counter_key"]
            items.append(
                {
                    "key": module["key"],
                    "label": module["label"],
                    "route": module["route"],
                    "enabled": True,
                    "badge_count": int(counters.get(counter_key, 0)) if counter_key else 0,
                }
            )
        return items
