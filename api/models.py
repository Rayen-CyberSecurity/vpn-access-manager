"""Request and response schemas. Validation lives here, not in the endpoints."""

from datetime import datetime
from ipaddress import IPv4Address
from typing import Literal

from pydantic import BaseModel, Field


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    department: str
    is_active: bool


class GatewayOut(BaseModel):
    id: int
    name: str
    region: str
    hostname: str
    max_sessions: int
    active_sessions: int


class SessionOut(BaseModel):
    id: int
    user_id: int
    username: str
    gateway_id: int
    gateway_name: str
    status: Literal["active", "closed"]
    client_ip: IPv4Address
    connected_at: datetime
    disconnected_at: datetime | None
    bytes_transferred: int


class SessionCreate(BaseModel):
    user_id: int
    gateway_id: int
    # IPv4Address is what produces the 422 for a malformed IP.
    # There is not one line of validation code anywhere in main.py.
    client_ip: IPv4Address


class SessionClose(BaseModel):
    bytes_transferred: int = Field(default=0, ge=0)
