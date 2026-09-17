"""Adaptador de gateway: llamadas HTTP a la API REST de Jira."""

import requests

from ..application.ports import JiraWorklogResult


class JiraRestWorklogGateway:
    def __init__(self, base_url: str, user: str, password: str, timeout: int = 30):
        self._base_url = base_url.rstrip("/")
        self._auth = (user, password)
        self._timeout = timeout

    def create(self, ticket: str, started: str, time_spent: str, comentario: str) -> JiraWorklogResult:
        url = f"{self._base_url}/rest/api/2/issue/{ticket}/worklog"
        resp = requests.post(
            url, json=self._payload(started, time_spent, comentario), auth=self._auth, timeout=self._timeout
        )
        return self._to_result(resp, expected_status=201)

    def update(
        self, ticket: str, worklog_id: str, started: str, time_spent: str, comentario: str
    ) -> JiraWorklogResult:
        """Reemplaza started/timeSpent/comment de un worklog ya existente (PUT, espera 200).

        worklog_id debe ser el id devuelto por Jira al crear el worklog
        (guardado por ExcelWorklogRepository en la columna 'WorklogID').
        """
        url = f"{self._base_url}/rest/api/2/issue/{ticket}/worklog/{worklog_id}"
        resp = requests.put(
            url, json=self._payload(started, time_spent, comentario), auth=self._auth, timeout=self._timeout
        )
        return self._to_result(resp, expected_status=200)

    @staticmethod
    def _payload(started: str, time_spent: str, comentario: str) -> dict:
        return {"started": started, "timeSpent": time_spent, "comment": comentario or ""}

    @staticmethod
    def _to_result(resp: requests.Response, expected_status: int) -> JiraWorklogResult:
        if resp.status_code == expected_status:
            return JiraWorklogResult(success=True, worklog_id=str(resp.json().get("id", "")))
        return JiraWorklogResult(success=False, error_message=f"{resp.status_code} {resp.text[:200]}")
