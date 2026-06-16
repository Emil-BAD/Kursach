from __future__ import annotations

from sqlalchemy.orm import Session

from api.db.models import User
from api.services.admin_dashboard_service import AdminDashboardService


class AdminBootstrapService:
    def __init__(self, db: Session):
        self.db = db
        self.dashboard_service = AdminDashboardService(db)

    def get_bootstrap(self, current_user: User) -> dict:
        return self.dashboard_service.get_bootstrap(current_user)
