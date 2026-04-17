import os
import requests
from typing import Optional, Any, Dict, List

# Convex deployment URL - should be set in environment
# For local dev, Convex runs on http://localhost:3000
CONVEX_SITE_URL = (
    os.getenv("CONVEX_SITE_URL") or os.getenv("SITE_URL") or "http://localhost:3000"
)
print(f"Convex client using URL: {CONVEX_SITE_URL}")


class ConvexClient:
    def __init__(self, site_url: Optional[str] = None):
        self.site_url = site_url or CONVEX_SITE_URL

    def _get_path(self, function_name: str) -> str:
        if function_name.startswith("/"):
            return function_name
        return function_name.replace("api:", "/api/").replace(":", "/")

    def query(self, function_name: str, args: Optional[Dict[str, Any]] = None) -> Any:
        path = self._get_path(function_name)
        url = f"{self.site_url}{path}"
        response = requests.post(url, json=args or {})
        if response.status_code != 200:
            raise Exception(f"Convex query failed: {response.text}")
        return response.json()

    def mutation(
        self, function_name: str, args: Optional[Dict[str, Any]] = None
    ) -> Any:
        path = self._get_path(function_name)
        url = f"{self.site_url}{path}"
        response = requests.post(url, json=args or {})
        if response.status_code != 200:
            raise Exception(f"Convex mutation failed: {response.text}")
        return response.json()

    def verify_password(self, email: str, password: str) -> Optional[Dict]:
        """Verify password by checking stored hash"""
        user = self.query("/api/getUserByEmail", {"email": email})
        if not user:
            return None

        # Get stored hash and verify using check_password_hash equivalent
        from werkzeug.security import check_password_hash

        stored_hash = user.get("passwordHash", "")
        if check_password_hash(stored_hash, password):
            return user
        return None


convex_client = ConvexClient()
