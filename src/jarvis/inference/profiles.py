"""Durable non-secret inference profiles and scope bindings for TB-04D."""
from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID, uuid4

from jarvis.connections.registry import ProviderRegistry
from jarvis.conversation.store import SQLiteConversationStore, _now


_SLUG = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")
_MODEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_SCOPE_TYPES = {"global", "project", "conversation", "agent", "task"}
_GLOBAL_SCOPE_ID = "*"


def _uuid(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("invalid_identifier")
    parsed = str(UUID(value))
    if parsed != value:
        raise ValueError("invalid_identifier")
    return parsed


def _model(value: object) -> str:
    if not isinstance(value, str) or _MODEL.fullmatch(value) is None:
        raise ValueError("invalid_model")
    return value


def _slug(value: object) -> str:
    if not isinstance(value, str) or _SLUG.fullmatch(value) is None:
        raise ValueError("invalid_profile_slug")
    return value


def _scope(scope_type: object, scope_id: object) -> tuple[str, str]:
    if not isinstance(scope_type, str) or scope_type not in _SCOPE_TYPES:
        raise ValueError("invalid_scope_type")
    if scope_type == "global":
        if scope_id not in (None, _GLOBAL_SCOPE_ID):
            raise ValueError("invalid_global_scope")
        return scope_type, _GLOBAL_SCOPE_ID
    if not isinstance(scope_id, str) or not scope_id.strip() or len(scope_id) > 256:
        raise ValueError("invalid_scope_id")
    return scope_type, scope_id.strip()


def _json_object(value: object, *, code: str) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(code)
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if len(encoded.encode("utf-8")) > 8192:
        raise ValueError(code)
    return dict(value)


class InferenceProfileStore:
    """Owns profile/binding persistence; never reads or stores credentials."""

    def __init__(self, path: Path | str):
        self.path = Path(path).expanduser().resolve()
        SQLiteConversationStore(self.path)  # Owns schema migration/version.

    @contextmanager
    def _connection(self):
        db = sqlite3.connect(str(self.path), timeout=10.0)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA foreign_keys = ON")
            db.execute("PRAGMA busy_timeout = 10000")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _decode_profile(row) -> dict:
        item = dict(row)
        item["configuration"] = json.loads(item.pop("configuration_json"))
        item["enabled"] = bool(item["enabled"])
        return item

    @staticmethod
    def _decode_binding(row) -> dict:
        item = dict(row)
        item["enabled"] = bool(item["enabled"])
        return item

    @staticmethod
    def configuration(
        connection_id: str,
        model: str,
        *,
        requirements: dict | None = None,
        constraints: dict | None = None,
    ) -> dict:
        return {
            "primary": {
                "connection_id": _uuid(connection_id),
                "model": _model(model),
            },
            "requirements": _json_object(
                requirements, code="invalid_profile_requirements",
            ),
            "constraints": _json_object(
                constraints, code="invalid_profile_constraints",
            ),
        }

    def create_profile(
        self,
        slug: str,
        name: str,
        *,
        connection_id: str,
        model: str,
        requirements: dict | None = None,
        constraints: dict | None = None,
    ) -> dict:
        slug = _slug(slug)
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 120:
            raise ValueError("invalid_profile_name")
        configuration = self.configuration(
            connection_id,
            model,
            requirements=requirements,
            constraints=constraints,
        )
        profile_id = str(uuid4())
        now = _now()
        with self._connection() as db:
            # Profiles may only target an existing AI connection identity.
            connection = db.execute(
                "SELECT provider_id FROM integration_connections WHERE id=?",
                (configuration["primary"]["connection_id"],),
            ).fetchone()
            if connection is None:
                raise ValueError("inference_profile_connection_not_found")
            descriptor = ProviderRegistry().get(connection["provider_id"])
            if descriptor is None or descriptor.provider_type != "ai_inference":
                raise ValueError("inference_profile_requires_ai_connection")
            db.execute(
                """INSERT INTO inference_profiles(
                    id,slug,name,configuration_json,enabled,created_at,updated_at
                ) VALUES (?,?,?,?,1,?,?)""",
                (
                    profile_id,
                    slug,
                    name.strip(),
                    json.dumps(
                        configuration,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    now,
                    now,
                ),
            )
        return self.get_profile(profile_id)

    def get_profile(self, profile_id: str) -> dict | None:
        profile_id = _uuid(profile_id)
        with self._connection() as db:
            row = db.execute(
                "SELECT * FROM inference_profiles WHERE id=?",
                (profile_id,),
            ).fetchone()
        return self._decode_profile(row) if row else None

    def get_by_slug(self, slug: str) -> dict | None:
        slug = _slug(slug)
        with self._connection() as db:
            row = db.execute(
                "SELECT * FROM inference_profiles WHERE slug=?",
                (slug,),
            ).fetchone()
        return self._decode_profile(row) if row else None

    def list_profiles(self) -> list[dict]:
        with self._connection() as db:
            rows = db.execute(
                "SELECT * FROM inference_profiles ORDER BY slug,id"
            ).fetchall()
        return [self._decode_profile(row) for row in rows]

    def bind(
        self,
        profile_id: str,
        *,
        scope_type: str,
        scope_id: str | None = None,
    ) -> dict:
        profile_id = _uuid(profile_id)
        scope_type, scope_id = _scope(scope_type, scope_id)
        now = _now()
        with self._connection() as db:
            profile = db.execute(
                "SELECT 1 FROM inference_profiles WHERE id=?",
                (profile_id,),
            ).fetchone()
            if profile is None:
                raise ValueError("inference_profile_not_found")
            existing = db.execute(
                "SELECT id FROM inference_bindings "
                "WHERE scope_type=? AND scope_id=?",
                (scope_type, scope_id),
            ).fetchone()
            if existing is None:
                binding_id = str(uuid4())
                db.execute(
                    """INSERT INTO inference_bindings(
                        id,scope_type,scope_id,profile_id,enabled,created_at,updated_at
                    ) VALUES (?,?,?,?,1,?,?)""",
                    (
                        binding_id, scope_type, scope_id,
                        profile_id, now, now,
                    ),
                )
            else:
                binding_id = existing["id"]
                db.execute(
                    """UPDATE inference_bindings
                       SET profile_id=?,enabled=1,updated_at=?
                       WHERE id=?""",
                    (profile_id, now, binding_id),
                )
        return self.get_binding(scope_type=scope_type, scope_id=scope_id)

    def get_binding(
        self, *, scope_type: str, scope_id: str | None = None,
    ) -> dict | None:
        scope_type, scope_id = _scope(scope_type, scope_id)
        with self._connection() as db:
            row = db.execute(
                "SELECT * FROM inference_bindings "
                "WHERE scope_type=? AND scope_id=?",
                (scope_type, scope_id),
            ).fetchone()
        return self._decode_binding(row) if row else None

    def set_profile_enabled(self, profile_id: str, enabled: bool) -> dict:
        profile_id = _uuid(profile_id)
        now = _now()
        with self._connection() as db:
            updated = db.execute(
                "UPDATE inference_profiles SET enabled=?,updated_at=? WHERE id=?",
                (1 if enabled else 0, now, profile_id),
            )
        if updated.rowcount != 1:
            raise ValueError("inference_profile_not_found")
        return self.get_profile(profile_id)

    def set_binding_enabled(
        self, *, scope_type: str, scope_id: str | None = None,
        enabled: bool,
    ) -> dict:
        scope_type, scope_id = _scope(scope_type, scope_id)
        now = _now()
        with self._connection() as db:
            updated = db.execute(
                """UPDATE inference_bindings
                   SET enabled=?,updated_at=?
                   WHERE scope_type=? AND scope_id=?""",
                (1 if enabled else 0, now, scope_type, scope_id),
            )
        if updated.rowcount != 1:
            raise ValueError("inference_binding_not_found")
        return self.get_binding(scope_type=scope_type, scope_id=scope_id)

    def ensure_general(
        self,
        *,
        connection_id: str,
        model: str,
    ) -> tuple[dict, dict, bool]:
        """One-time migration from the pre-profile explicit desktop selection.

        Existing `general` configuration is never overwritten here.
        """
        existing = self.get_by_slug("general")
        created = False
        if existing is None:
            existing = self.create_profile(
                "general",
                "Geral",
                connection_id=connection_id,
                model=model,
                requirements={
                    "streaming": True,
                    "structured_output": True,
                },
                constraints={
                    "locality": "cloud_allowed",
                },
            )
            created = True

        binding = self.get_binding(scope_type="global")
        if binding is None:
            binding = self.bind(existing["id"], scope_type="global")
        return existing, binding, created
