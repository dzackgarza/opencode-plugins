"""Improved Jules CLI - API client."""

import os
from typing import Optional
import requests

BASE_URL = "https://jules.googleapis.com/v1alpha"


class JulesAPI:
    """Jules REST API client."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("JULES_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key required. Set JULES_API_KEY env var or pass to constructor."
            )
        self.headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        url = f"{BASE_URL}{endpoint}"
        resp = requests.request(method, url, headers=self.headers, **kwargs)
        resp.raise_for_status()
        return resp.json() if resp.content else {}

    # Sessions
    def list_sessions(
        self, page_size: int = 30, page_token: Optional[str] = None
    ) -> dict:
        params = {"pageSize": page_size}
        if page_token:
            params["pageToken"] = page_token
        return self._request("GET", "/sessions", params=params)

    # Sources
    def list_sources(
        self, page_size: int = 100, page_token: Optional[str] = None
    ) -> dict:
        """List available sources."""
        params = {"pageSize": page_size}
        if page_token:
            params["pageToken"] = page_token
        return self._request("GET", "/sources", params=params)

    def get_session(self, session_id: str) -> dict:
        return self._request("GET", f"/sessions/{session_id}")

    def find_source_by_repo(self, owner: str, repo: str) -> Optional[dict]:
        """Find a source by owner/repo name."""
        page_token = None
        while True:
            result = self.list_sources(page_token=page_token)
            for source in result.get("sources", []):
                gh = source.get("githubRepo", {})
                if gh.get("owner") == owner and gh.get("repo") == repo:
                    return source
            page_token = result.get("nextPageToken")
            if not page_token:
                return None

    def create_session(
        self,
        prompt: str,
        title: Optional[str] = None,
        source_context: Optional[dict] = None,
        require_plan_approval: bool = False,
        automation_mode: Optional[str] = None,
    ) -> dict:
        body = {"prompt": prompt}
        if title:
            body["title"] = title
        if source_context:
            body["sourceContext"] = source_context
        if require_plan_approval:
            body["requirePlanApproval"] = True
        if automation_mode:
            body["automationMode"] = automation_mode
        return self._request("POST", "/sessions", json=body)

    def delete_session(self, session_id: str) -> dict:
        return self._request("DELETE", f"/sessions/{session_id}")

    def send_message(self, session_id: str, prompt: str) -> dict:
        return self._request(
            "POST", f"/sessions/{session_id}:sendMessage", json={"prompt": prompt}
        )

    def approve_plan(self, session_id: str) -> dict:
        return self._request("POST", f"/sessions/{session_id}:approvePlan", json={})

    # Activities
    def list_activities(
        self, session_id: str, page_size: int = 50, page_token: Optional[str] = None
    ) -> dict:
        params = {"pageSize": page_size}
        if page_token:
            params["pageToken"] = page_token
        return self._request("GET", f"/sessions/{session_id}/activities", params=params)

    def get_activity(self, session_id: str, activity_id: str) -> dict:
        return self._request("GET", f"/sessions/{session_id}/activities/{activity_id}")
