"""VPN Access Manager REST API."""

from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query, status

from api.db import query, transaction
from api.models import GatewayOut, SessionClose, SessionCreate, SessionOut
from api.security import require_api_key


app = FastAPI(
    title="VPN Access Manager",
    version="0.1.0",
    description="REST API for managing VPN sessions and gateways.",
)


SESSION_SELECT = """
    SELECT
        s.id,
        s.user_id,
        u.username,
        d.name AS department,
        s.gateway_id,
        g.name AS gateway_name,
        s.status,
        host(s.client_ip) AS client_ip,
        s.connected_at,
        s.disconnected_at,
        s.bytes_transferred
    FROM session s
    JOIN vpn_user u
        ON u.id = s.user_id
    JOIN department d
        ON d.id = u.department_id
    JOIN gateway g
        ON g.id = s.gateway_id
"""


@app.get("/gateways", response_model=list[GatewayOut])
def list_gateways():
    """Return all gateways with their number of active sessions."""

    with query() as conn:
        rows = conn.execute(
            """
            SELECT
                g.id,
                g.name,
                g.region,
                host(g.public_ip) AS public_ip,
                g.max_sessions,
                COUNT(s.id) AS active_sessions
            FROM gateway g
            LEFT JOIN session s
                ON s.gateway_id = g.id
                AND s.status = 'active'
            GROUP BY g.id
            ORDER BY g.name
            """
        ).fetchall()

    return rows


@app.get("/sessions", response_model=list[SessionOut])
def list_sessions(
    status_filter: Literal["active", "closed"] | None = Query(
        default=None,
        alias="status",
    ),
    gateway: str | None = Query(
        default=None,
        description="Gateway name",
    ),
):
    """Return sessions, optionally filtered by status or gateway."""

    sql = SESSION_SELECT
    conditions = []
    params = []

    if status_filter is not None:
        conditions.append("s.status = %s")
        params.append(status_filter)

    if gateway is not None:
        conditions.append("g.name = %s")
        params.append(gateway)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += " ORDER BY s.connected_at DESC, s.id DESC"

    with query() as conn:
        rows = conn.execute(sql, params).fetchall()

    return rows


@app.get("/sessions/{session_id}", response_model=SessionOut)
def get_session(session_id: int):
    """Return one session."""

    with query() as conn:
        row = conn.execute(
            SESSION_SELECT + " WHERE s.id = %s",
            (session_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} does not exist.",
        )

    return row


@app.post(
    "/sessions",
    response_model=SessionOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
def open_session(payload: SessionCreate):
    """Open a session after validating the user, gateway and capacity."""

    with transaction() as conn:

        gateway = conn.execute(
            """
            SELECT id, name, max_sessions
            FROM gateway
            WHERE id = %s
            """,
            (payload.gateway_id,),
        ).fetchone()

        if gateway is None:
            raise HTTPException(
                status_code=404,
                detail=f"Gateway {payload.gateway_id} does not exist.",
            )

        user = conn.execute(
            """
            SELECT id, username
            FROM vpn_user
            WHERE id = %s
            """,
            (payload.user_id,),
        ).fetchone()

        if user is None:
            raise HTTPException(
                status_code=404,
                detail=f"User {payload.user_id} does not exist.",
            )

        active = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM session
            WHERE gateway_id = %s
              AND status = 'active'
            """,
            (payload.gateway_id,),
        ).fetchone()["count"]

        if active >= gateway["max_sessions"]:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Gateway {gateway['name']} is at capacity "
                    f"({active}/{gateway['max_sessions']} active sessions)."
                ),
            )

        new_session = conn.execute(
            """
            INSERT INTO session (
                user_id,
                gateway_id,
                status,
                client_ip
            )
            VALUES (%s, %s, 'active', %s)
            RETURNING id
            """,
            (
                payload.user_id,
                payload.gateway_id,
                str(payload.client_ip),
            ),
        ).fetchone()

        new_id = new_session["id"]

        row = conn.execute(
            SESSION_SELECT + " WHERE s.id = %s",
            (new_id,),
        ).fetchone()

    return row


@app.post(
    "/sessions/{session_id}/close",
    response_model=SessionOut,
    dependencies=[Depends(require_api_key)],
)
def close_session(session_id: int, payload: SessionClose):
    """Close an active session."""

    with transaction() as conn:

        existing = conn.execute(
            """
            SELECT id, status
            FROM session
            WHERE id = %s
            """,
            (session_id,),
        ).fetchone()

        if existing is None:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} does not exist.",
            )

        if existing["status"] == "active":
            conn.execute(
                """
                UPDATE session
                SET
                    status = 'closed',
                    disconnected_at = now(),
                    bytes_transferred = %s
                WHERE id = %s
                """,
                (
                    payload.bytes_transferred,
                    session_id,
                ),
            )

        row = conn.execute(
            SESSION_SELECT + " WHERE s.id = %s",
            (session_id,),
        ).fetchone()

    return row
