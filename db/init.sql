-- ============================================================
-- VPN Access Manager
-- Database schema and initial data
-- ============================================================

DROP TABLE IF EXISTS session, vpn_user, gateway, department CASCADE;


-- ============================================================
-- 1. Department
-- ============================================================

CREATE TABLE department (
    id            SERIAL PRIMARY KEY,
    name          TEXT NOT NULL UNIQUE,
    contact_email TEXT NOT NULL
);


-- ============================================================
-- 2. VPN User
-- ============================================================

CREATE TABLE vpn_user (
    id            SERIAL PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    email         TEXT NOT NULL,
    department_id INT NOT NULL
        REFERENCES department(id)
);


-- ============================================================
-- 3. Gateway
-- ============================================================

CREATE TABLE gateway (
    id           SERIAL PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    region       TEXT NOT NULL,
    public_ip    INET NOT NULL,
    max_sessions INT NOT NULL,

    CONSTRAINT gateway_capacity_positive
        CHECK (max_sessions > 0)
);


-- ============================================================
-- 4. Session
-- ============================================================

CREATE TABLE session (
    id                SERIAL PRIMARY KEY,

    status            TEXT NOT NULL,

    client_ip         INET NOT NULL,

    connected_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    disconnected_at   TIMESTAMPTZ,

    bytes_transferred BIGINT NOT NULL DEFAULT 0,

    user_id           INT NOT NULL
        REFERENCES vpn_user(id),

    gateway_id        INT NOT NULL
        REFERENCES gateway(id),

    CONSTRAINT session_status_valid
        CHECK (status IN ('active', 'closed')),

    CONSTRAINT session_time_order
        CHECK (
            disconnected_at IS NULL
            OR disconnected_at >= connected_at
        ),

    CONSTRAINT active_session_has_no_disconnect_time
        CHECK (
            status <> 'active'
            OR disconnected_at IS NULL
        )
);


-- ============================================================
-- Seed data
-- ============================================================

INSERT INTO department (name, contact_email)
VALUES
    ('Engineering', 'engineering@example.com'),
    ('Sales',       'sales@example.com'),
    ('Support',     'support@example.com');


INSERT INTO vpn_user (username, email, department_id)
VALUES
    ('amuller',  'anna.mueller@example.com',  1),
    ('bschmidt', 'ben.schmidt@example.com',   1),
    ('cweber',   'clara.weber@example.com',   1),
    ('dfischer', 'david.fischer@example.com', 2),
    ('ekoch',    'eva.koch@example.com',      2),
    ('fbauer',   'felix.bauer@example.com',   3),
    ('gwolf',    'greta.wolf@example.com',    3),
    ('hklein',   'hannes.klein@example.com',  3);


INSERT INTO gateway (name, region, public_ip, max_sessions)
VALUES
    ('gw-eu-1', 'Frankfurt', '203.0.113.10', 3),
    ('gw-eu-2', 'Berlin',    '203.0.113.20', 5),
    ('gw-us-1', 'Ashburn',   '203.0.113.30', 4);


INSERT INTO session (
    status,
    client_ip,
    connected_at,
    user_id,
    gateway_id
)
VALUES
    (
        'active',
        '192.168.10.11',
        now() - interval '2 hours',
        1,
        1
    ),
    (
        'active',
        '192.168.10.12',
        now() - interval '90 minutes',
        2,
        1
    ),
    (
        'active',
        '192.168.10.13',
        now() - interval '30 minutes',
        3,
        1
    ),
    (
        'active',
        '192.168.20.41',
        now() - interval '45 minutes',
        4,
        2
    );


INSERT INTO session (
    status,
    client_ip,
    connected_at,
    disconnected_at,
    bytes_transferred,
    user_id,
    gateway_id
)
VALUES
    (
        'closed',
        '192.168.10.11',
        now() - interval '2 days',
        now() - interval '47 hours',
        15728640,
        1,
        1
    ),
    (
        'closed',
        '192.168.20.55',
        now() - interval '1 day',
        now() - interval '23 hours',
        3145728,
        5,
        2
    ),
    (
        'closed',
        '10.20.30.66',
        now() - interval '5 hours',
        now() - interval '4 hours',
        52428800,
        6,
        3
    );
