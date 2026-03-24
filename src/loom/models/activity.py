"""Activity feed domain models."""

from datetime import datetime

from pydantic import BaseModel


class ActivityEvent(BaseModel):
    """A single event in the activity feed."""

    id: str
    event_type: str
    """skill_submitted | capability_submitted | trust_promoted | trust_demoted | eval_completed."""
    timestamp: datetime
    slug: str
    name: str
    detail: str
    previous_value: str | None = None
    new_value: str | None = None
