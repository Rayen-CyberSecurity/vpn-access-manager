"""VPN Access Manager — HTTP API.

Endpoints
    GET  /health                    liveness
    GET  /users                     user list for the desktop client
    GET  /gateways                  overview with live active-session counts
    GET  /sessions                  filterable session list
    GET  /sessions/{id}             one session
    POST /sessions                  open a session      [X-API-Key]
    POST /sessions/{id}/close       close a session     [X-API-Key]
"""

from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query, status
from psycopg import errors

from api.db import query, transaction
from api.models import (
    GatewayOut,
    SessionClose,
    SessionCreate,
    SessionOut,
    UserOut,
)
from api.security import require_api_key

app = FastAPI(
    title="VPN Access Manager",
    version="1.0.0",
    description=(
        "Manages VPN sessions across gateways and enforces per-gateway "
        "capacity in a single database transaction."
    ),
)

# client_ip is cast to text so Pydantic receives a plain string and parses it
# back into IPv4Address itself, instead of depending on the driver's INET
# adapter returning one type or another.
SESSION_SELECT = """
    SELECT s.id, s.user_id, u.username,
           s.gateway_id, g.name AS gateway_name,
           s.status, host(s.client_ip)  AS client_ip,
           s.connected_at, s.disconnected_at, s.bytes_transferred
    FROM   session s
    JOIN   vpn_user u ON u.id = s.user_id
    JOIN   gateway  g ON g.id = s.gateway_id
"""


# ----------------------------------------------------------------- reads


@app.get("/health")
def health() -> dict:
    with query() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok"}


@app.get("/users", response_model=list[UserOut])
def list_users():
    with query() as conn:
        rows = conn.execute(
            """
            SELECT u.id, u.username, u.full_name,
                   d.name AS department, u.is_active
            FROM   vpn_user u
            JOIN   department d ON d.id = u.department_id
            ORDER  BY u.username
            """
        ).fetchall()
    return rows


@app.get("/gateways", response_model=list[GatewayOut])
def list_gateways():
    """LEFT JOIN, not JOIN: a gateway with zero active sessions must still
    appear in the overview — otherwise an empty gateway looks like it does
    not exist and nobody can connect to it."""
    with query() as conn:
        rows = conn.execute(
            """
            SELECT g.id, g.name, g.region, g.hostname, g.max_sessions,
                   COUNT(s.id) AS active_sessions
            FROM   gateway g
            LEFT JOIN session s
                   ON s.gateway_id = g.id AND s.status = 'active'
            GROUP  BY g.id
            ORDER  BY g.name
            """
        ).fetchall()
    return rows


@app.get("/sessions", response_model=list[SessionOut])
def list_sessions(
    status_filter: Literal["active", "closed"] | None = Query(
        default=None, alias="status"
    ),
    gateway: str | None = Query(default=None, description="gateway name"),
    user: str | None = Query(default=None, description="username"),
):
    sql = SESSION_SELECT
    where, params = [], []

    if status_filter is not None:
        where.append("s.status = %s")
        params.append(status_filter)
    if gateway is not None:
        where.append("g.name = %s")
        params.append(gateway)
    if user is not None:
        where.append("u.username = %s")
        params.append(user)

    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY s.connected_at DESC, s.id DESC"

    with query() as conn:
        rows = conn.execute(sql, params).fetchall()
    return rows


@app.get("/sessions/{session_id}", response_model=SessionOut)
def get_session(session_id: int):
    with query() as conn:
        row = conn.execute(
            SESSION_SELECT + " WHERE s.id = %s", (session_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(404, f"Session {session_id} does not exist.")
    return row


# ---------------------------------------------------------------- writes


@app.post(
    "/sessions",
    response_model=SessionOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
def open_session(payload: SessionCreate):
    """Open a session, refusing if the gateway is at capacity.

    Why not a CHECK constraint?
        A row-level CHECK sees only the row being written. The rule is
        "how many rows with this gateway_id have status 'active'" — a
        condition over a set, not over a row.

    Why not a trigger?
        A trigger could do it, but it raises a generic database error. In
        the API the rule can answer with a meaningful 409 and a message the
        desktop client shows verbatim.

    Why SELECT ... FOR UPDATE?
        Without the row lock two requests arriving together both read
        active = 2 against max = 3, both pass the check, and both insert,
        leaving the gateway at 4 — exactly the bug this project exists to
        prevent. FOR UPDATE locks the gateway row, so the second transaction
        waits for the first to commit and then re-reads the true count.
        Requests for different gateways lock different rows and stay parallel.
    """
    with transaction() as conn:
        gw = conn.execute(
            "SELECT id, name, max_sessions FROM gateway WHERE id = %s FOR UPDATE",
            (payload.gateway_id,),
        ).fetchone()
        if gw is None:
            raise HTTPException(404, f"Gateway {payload.gateway_id} does not exist.")

        usr = conn.execute(
            "SELECT id, username, is_active FROM vpn_user WHERE id = %s",
            (payload.user_id,),
        ).fetchone()
        if usr is None:
            raise HTTPException(404, f"User {payload.user_id} does not exist.")
        if not usr["is_active"]:
            raise HTTPException(403, f"User {usr['username']} is deactivated.")

        active = conn.execute(
            "SELECT COUNT(*) AS n FROM session "
            "WHERE gateway_id = %s AND status = 'active'",
            (gw["id"],),
        ).fetchone()["n"]

        if active >= gw["max_sessions"]:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Gateway {gw['name']} is at capacity "
                f"({active}/{gw['max_sessions']} active sessions). "
                f"Close a session or choose another gateway.",
            )

        try:
            new_id = conn.execute(
                """
                INSERT INTO session (user_id, gateway_id, status, client_ip)
                VALUES (%s, %s, 'active', %s)
                RETURNING id
                """,
                (payload.user_id, payload.gateway_id, str(payload.client_ip)),
            ).fetchone()["id"]
        except errors.UniqueViolation:
            # session_one_active fired
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"User {usr['username']} already has an active session "
                f"on {gw['name']}.",
            )

        return conn.execute(
            SESSION_SELECT + " WHERE s.id = %s", (new_id,)
        ).fetchone()


@app.post(
    "/sessions/{session_id}/close",
    response_model=SessionOut,
    dependencies=[Depends(require_api_key)],
)
def close_session(session_id: int, payload: SessionClose):
    """Close a session. Idempotent: closing an already-closed session returns
    the existing record unchanged, including its original byte count, rather
    than erroring or overwriting."""
    with transaction() as conn:
        row = conn.execute(
            "SELECT id, status FROM session WHERE id = %s FOR UPDATE",
            (session_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(404, f"Session {session_id} does not exist.")

        if row["status"] == "active":
            conn.execute(
                """
                UPDATE session
                SET    status = 'closed',
                       disconnected_at = now(),
                       bytes_transferred = %s
                WHERE  id = %s
                """,
                (payload.bytes_transferred, session_id),
            )

        return conn.execute(
            SESSION_SELECT + " WHERE s.id = %s", (session_id,)
        ).fetchone()
