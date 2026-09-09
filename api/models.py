"""Pydantic models for API requests and responses."""

from datetime import datetime
from ipaddress import IPv4Address
from typing import Literal

from pydantic import BaseModel, Field


class GatewayOut(BaseModel):
    id: int
    name: str
    region: str
    public_ip: IPv4Address
    max_sessions: int
    active_sessions: int


class SessionOut(BaseModel):
    id: int
    user_id: int
    username: str
    department: str
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
    client_ip: IPv4Address


class SessionClose(BaseModel):
    bytes_transferred: int = Field(default=0, ge=0)
