"""Durable non-secret integration connection state."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID, uuid4

from jarvis.conversation.store import SQLiteConversationStore, _now


class ConnectionStore:
    def __init__(self, path: Path | str):
        self.path = Path(path).expanduser().resolve()
        SQLiteConversationStore(self.path)  # Owns schema migration/version.

    @contextmanager
    def _connection(self):
        db = sqlite3.connect(str(self.path), timeout=10.0)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA busy_timeout = 10000")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _id(value: str) -> str:
        value = str(UUID(value))
        return value

    @staticmethod
    def _decode(row) -> dict:
        item = dict(row)
        item["enabled"] = bool(item["enabled"])
        item["configuration"] = json.loads(item.pop("configuration_json"))
        item["observed_permissions"] = json.loads(
            item.pop("observed_permissions_json")
        )
        return item

    def create(
        self, provider_id: str, *, configuration: dict | None = None,
        credential_ref: str | None = None,
    ) -> dict:
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise ValueError("invalid_provider_id")
        if configuration is None:
            configuration = {}
        if not isinstance(configuration, dict):
            raise ValueError("invalid_configuration")
        connection_id = str(uuid4())
        now = _now()
        if credential_ref is None:
            credential_ref = f"wincred:{connection_id}"
        if (not isinstance(credential_ref, str)
                or not credential_ref.strip()
                or len(credential_ref) > 256):
            raise ValueError("invalid_credential_ref")
        credential_ref = credential_ref.strip()
        with self._connection() as db:
            db.execute(
                """INSERT INTO integration_connections(
                    id,provider_id,credential_ref,configuration_json,
                    created_at,updated_at
                ) VALUES (?,?,?,?,?,?)""",
                (
                    connection_id, provider_id.strip(), credential_ref,
                    json.dumps(configuration, ensure_ascii=False, sort_keys=True),
                    now, now,
                ),
            )
        return self.get(connection_id)

    def get(self, connection_id: str) -> dict | None:
        connection_id = self._id(connection_id)
        with self._connection() as db:
            row = db.execute(
                "SELECT * FROM integration_connections WHERE id=?",
                (connection_id,),
            ).fetchone()
        return self._decode(row) if row else None

    def list(self) -> list[dict]:
        with self._connection() as db:
            rows = db.execute(
                "SELECT * FROM integration_connections "
                "ORDER BY provider_id,created_at,id"
            ).fetchall()
        return [self._decode(row) for row in rows]

    def list_by_provider(self, provider_id: str) -> list[dict]:
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise ValueError("invalid_provider_id")
        with self._connection() as db:
            rows = db.execute(
                "SELECT * FROM integration_connections "
                "WHERE provider_id=? ORDER BY created_at,id",
                (provider_id.strip(),),
            ).fetchall()
        return [self._decode(row) for row in rows]

    def update_configuration(
        self, connection_id: str, configuration: dict,
    ) -> dict:
        connection_id = self._id(connection_id)
        if not isinstance(configuration, dict):
            raise ValueError("invalid_configuration")
        now = _now()
        with self._connection() as db:
            updated = db.execute(
                """UPDATE integration_connections
                   SET configuration_json=?,updated_at=?
                   WHERE id=?""",
                (
                    json.dumps(
                        configuration, ensure_ascii=False, sort_keys=True
                    ),
                    now, connection_id,
                ),
            )
        if updated.rowcount != 1:
            raise KeyError("unknown_connection")
        return self.get(connection_id)

    def record_inspection(
        self, connection_id: str, *,
        display_identity: str | None,
        external_account_ref: str | None,
        observed_permissions: list[str],
        availability: str,
        error_code: str | None,
    ) -> dict:
        connection_id = self._id(connection_id)
        if availability not in {
            "unknown", "available", "unavailable", "auth_required",
            "permission_insufficient", "error",
        }:
            raise ValueError("invalid_availability")
        if (not isinstance(observed_permissions, list)
                or not all(isinstance(x, str) for x in observed_permissions)):
            raise ValueError("invalid_permissions")
        now = _now()
        with self._connection() as db:
            updated = db.execute(
                """UPDATE integration_connections
                   SET display_identity=?,external_account_ref=?,
                       observed_permissions_json=?,availability=?,
                       last_error_code=?,last_verified_at=?,updated_at=?
                   WHERE id=?""",
                (
                    display_identity, external_account_ref,
                    json.dumps(sorted(set(observed_permissions))),
                    availability, error_code, now, now, connection_id,
                ),
            )
        if updated.rowcount != 1:
            raise KeyError("unknown_connection")
        return self.get(connection_id)

    def set_enabled(self, connection_id: str, enabled: bool) -> dict:
        connection_id = self._id(connection_id)
        now = _now()
        with self._connection() as db:
            updated = db.execute(
                "UPDATE integration_connections SET enabled=?,updated_at=? WHERE id=?",
                (1 if enabled else 0, now, connection_id),
            )
        if updated.rowcount != 1:
            raise KeyError("unknown_connection")
        return self.get(connection_id)

    def delete(self, connection_id: str) -> bool:
        connection_id = self._id(connection_id)
        with self._connection() as db:
            removed = db.execute(
                "DELETE FROM integration_connections WHERE id=?",
                (connection_id,),
            )
        return removed.rowcount == 1
