from dataclasses import dataclass, field
from typing import Dict, Set, Optional
from threading import Lock


@dataclass
class AppState:
    user_id: Optional[str] = None
    display_name: Optional[str] = None
    avatar_data: Optional[str] = None

    listen_port: Optional[int] = None
    local_ip: Optional[str] = None
    broadcast_ip: Optional[str] = None
    lock: Lock = field(default_factory=Lock, repr=False, compare=False)

    # user object (stored in peers dict) has the following fields
    # TODO add the avatar fields
    # "ip", "display_name, "status","last_seen"

    peers: Dict[str, dict] = field(default_factory=dict)
    following: Set[str] = field(default_factory=set)
    followers: Set[str] = field(default_factory=set)
    revoked_token: Dict[str, float] = field(default_factory=dict)

    # used for referencing posts for like/unlike
    received_posts: Dict[str, dict] = field(default_factory=dict)
    sent_posts: Dict[str, dict] = field(default_factory=dict)

    # used for managing groups
    owned_groups: Dict[str, dict] = field(
        default_factory=dict
    )  # groups owned by this client
    joined_groups: Dict[str, dict] = field(
        default_factory=dict
    )  # groups this client joined and doesn't own
    # ACK
    pending_acks: Dict[str, dict] = field(default_factory=dict)

    # TICTACTOE INFORMATION
    active_games: Dict[str, dict] = field(default_factory=dict)
    received_moves: Set[tuple] = field(default_factory=set)  # (GAMEID, TURN)

    # FILE TRANSFER
    pending_file_offers: Dict[str, dict] = field(default_factory=dict)  # FILEID → offer metadata
    file_transfers: Dict[str, dict] = field(default_factory=dict)       # FILEID → chunks, etc.
