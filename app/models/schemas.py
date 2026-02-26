"""Data models for LokSarthi — Citizen profiles, schemes, sessions."""
from dataclasses import dataclass, field, asdict
from typing import Optional
import time
import uuid


@dataclass
class CitizenProfile:
    """Represents a citizen's profile extracted from conversation."""
    age: Optional[int] = None
    gender: Optional[str] = None          # male, female, other
    state: Optional[str] = None
    district: Optional[str] = None
    occupation: Optional[str] = None      # farmer, labourer, vendor, student, etc.
    category: Optional[str] = None        # general, sc, st, obc, minority
    annual_income: Optional[int] = None
    bpl_status: Optional[bool] = None
    disability: Optional[bool] = None
    marital_status: Optional[str] = None  # married, widowed, single, divorced
    land_ownership: Optional[bool] = None
    education_level: Optional[str] = None # none, primary, secondary, graduate
    family_members: Optional[int] = None
    children_count: Optional[int] = None
    children_in_school: Optional[bool] = None
    pregnant_in_family: Optional[bool] = None
    senior_in_family: Optional[bool] = None

    def completeness_score(self) -> float:
        """Return 0-1 score of how complete the profile is."""
        critical_fields = ['age', 'gender', 'state', 'occupation', 'category', 'annual_income']
        filled = sum(1 for f in critical_fields if getattr(self, f) is not None)
        return filled / len(critical_fields)

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class Session:
    """Conversation session for a user."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    language: str = "hi"
    current_pillar: str = "greeting"       # greeting, scheme_discovery, rti, financial
    profile: CitizenProfile = field(default_factory=CitizenProfile)
    conversation_history: list = field(default_factory=list)
    matched_schemes: list = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def add_message(self, role: str, content: str):
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        self.updated_at = time.time()

    def get_recent_history(self, n: int = 10) -> list:
        """Get last n messages for context."""
        return self.conversation_history[-n:]

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "language": self.language,
            "current_pillar": self.current_pillar,
            "profile": self.profile.to_dict(),
            "conversation_history": self.conversation_history[-20:],  # Keep last 20
            "matched_schemes": self.matched_schemes,
            "created_at": int(self.created_at),
            "updated_at": int(self.updated_at),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        profile = CitizenProfile(**data.get("profile", {}))
        return cls(
            session_id=data["session_id"],
            user_id=data.get("user_id"),
            language=data.get("language", "hi"),
            current_pillar=data.get("current_pillar", "greeting"),
            profile=profile,
            conversation_history=data.get("conversation_history", []),
            matched_schemes=data.get("matched_schemes", []),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )
