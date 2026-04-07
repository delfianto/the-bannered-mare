"""Health check service"""

import os

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.core.config import settings


class HealthService:
    """Service for health check related business logic"""

    def __init__(self, db: Session):
        self.db = db

    def get_db_status(self) -> bool:
        """Check database connection status"""
        try:
            _ = self.db.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def get_storage_status(self) -> bool:
        """Check if storage directory is accessible and writable"""
        try:
            if not os.path.exists(settings.storage_path):
                return False

            # Check if we can write to it
            test_file = os.path.join(settings.storage_path, ".health_check")
            with open(test_file, "w") as f:
                f.write("ok")
            os.remove(test_file)
            return True
        except Exception:
            return False
