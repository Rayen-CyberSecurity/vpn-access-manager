-- ============================================================
-- VPN Access Manager — schema and seed data
-- Runs automatically on first container start (empty volume).
-- ============================================================

DROP TABLE IF EXISTS session, vpn_user, gateway, department CASCADE;

-- ---------- 1. department ----------
CREATE TABLE department (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    cost_center TEXT NOT NULL
);

-- ---------- 2. vpn_user ----------
-- "user" is reserved in PostgreSQL, hence vpn_user.
CREATE TABLE vpn_user (
    id            SERIAL PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    full_name     TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    department_id INT  NOT NULL
        REFERENCES department(id) ON DELETE RESTRICT,
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------- 3. gateway ----------
CREATE TABLE gateway (
    id           SERIAL PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    region       TEXT NOT NULL,
    hostname     TEXT NOT NULL UNIQUE,
    max_sessions INT  NOT NULL,
    CONSTRAINT gateway_capacity_positive CHECK (max_sessions > 0)
);

-- ---------- 4. session ----------
-- Associative entity: resolves the M:N between vpn_user and gateway
-- and carries its own attributes (times, IP, volume).
CREATE TABLE session (
    id                SERIAL PRIMARY KEY,
    user_id           INT NOT NULL
        REFERENCES vpn_user(id) ON DELETE RESTRICT,
    gateway_id        INT NOT NULL
        REFERENCES gateway(id) ON DELETE RESTRICT,
    status            TEXT NOT NULL,
    client_ip         INET NOT NULL,
    connected_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    disconnected_at   TIMESTAMPTZ,
    bytes_transferred BIGINT NOT NULL DEFAULT 0,

    CONSTRAINT session_status_valid
        CHECK (status IN ('active', 'closed')),

    CONSTRAINT session_bytes_nonnegative
        CHECK (bytes_transferred >= 0),

    -- a session can never end before it started
    CONSTRAINT session_time_order
        CHECK (disconnected_at IS NULL OR disconnected_at >= connected_at),

    -- status and timestamp can never contradict each other
    CONSTRAINT session_state_consistent
        CHECK (
            (status = 'active' AND disconnected_at IS NULL)
         OR (status = 'closed' AND disconnected_at IS NOT NULL)
        )
);

-- Partial unique index: one user cannot hold two ACTIVE sessions on the
-- same gateway, while any number of CLOSED ones may repeat.
CREATE UNIQUE INDEX session_one_active
    ON session (user_id, gateway_id)
    WHERE status = 'active';

CREATE INDEX session_gateway_active
    ON session (gateway_id) WHERE status = 'active';

-- NOTE: the capacity rule (active sessions <= gateway.max_sessions) is
-- deliberately absent here. A CHECK sees only the row being written; the
-- rule is a condition over a SET of rows. It is enforced in the API,
-- inside one transaction, with SELECT ... FOR UPDATE.

-- ============================================================
-- Seed data — shaped for the demo and the tests, not random.
-- ============================================================

INSERT INTO department (name, cost_center) VALUES
    ('Engineering', 'CC-1000'),
    ('Sales',       'CC-2000'),
    ('Support',     'CC-3000');

INSERT INTO vpn_user (username, full_name, email, department_id) VALUES
    ('amuller',  'Anna Mueller',  'anna.mueller@example.com',  1),
    ('bschmidt', 'Ben Schmidt',   'ben.schmidt@example.com',   1),
    ('cweber',   'Clara Weber',   'clara.weber@example.com',   1),
    ('dfischer', 'David Fischer', 'david.fischer@example.com', 2),
    ('ekoch',    'Eva Koch',      'eva.koch@example.com',      2),
    ('fbauer',   'Felix Bauer',   'felix.bauer@example.com',   3),
    ('gwolf',    'Greta Wolf',    'greta.wolf@example.com',    3),
    ('hklein',   'Hannes Klein',  'hannes.klein@example.com',  3);

INSERT INTO gateway (name, region, hostname, max_sessions) VALUES
    ('gw-eu-1', 'Frankfurt', 'gw-eu-1.vpn.example.com', 3),
    ('gw-eu-2', 'Berlin',    'gw-eu-2.vpn.example.com', 5),
    ('gw-us-1', 'Ashburn',   'gw-us-1.vpn.example.com', 4);

-- gw-eu-1 deliberately FULL (3/3): the capacity refusal fires on the
-- first click in the video, with no setup.
INSERT INTO session (user_id, gateway_id, status, client_ip, connected_at) VALUES
    (1, 1, 'active', '192.168.10.11', now() - interval '2 hours'),
    (2, 1, 'active', '192.168.10.12', now() - interval '90 minutes'),
    (3, 1, 'active', '192.168.10.13', now() - interval '30 minutes');

-- id 4: the session the curl walkthrough closes twice.
INSERT INTO session (user_id, gateway_id, status, client_ip, connected_at) VALUES
    (4, 2, 'active', '192.168.20.41', now() - interval '45 minutes');

-- Closed history. Session 5 repeats user 1 on gw-eu-1 — proof the partial
-- index restricts only ACTIVE rows.
INSERT INTO session (user_id, gateway_id, status, client_ip,
                     connected_at, disconnected_at, bytes_transferred) VALUES
    (1, 1, 'closed', '192.168.10.11',
        now() - interval '2 days',  now() - interval '47 hours', 15728640),
    (5, 2, 'closed', '192.168.20.55',
        now() - interval '1 day',   now() - interval '23 hours',  3145728),
    (6, 3, 'closed', '10.20.30.66',
        now() - interval '5 hours', now() - interval '4 hours',  52428800);

-- gw-us-1 now has ZERO active sessions on purpose: it only appears in the
-- overview because of the LEFT JOIN.
