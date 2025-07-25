from dataclasses import dataclass, field
from typing import Dict, Set, Optional

@dataclass
class AppState:
    user_id: Optional[str] = None
    display_name: Optional[str] = None
    avatar_data: Optional[str] = None

    local_ip: Optional[str] = None
    broadcast_ip: Optional[str] = None

    peers: Dict[str, dict] = field(default_factory=dict)
    following: Set[str] = field(default_factory=set)
    followers: Set[str] = field(default_factory=set)
    revoked_token: Dict[str, float] = field(default_factory=dict)