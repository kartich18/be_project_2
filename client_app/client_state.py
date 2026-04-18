"""
client_state — in-memory machine identity state for the client app.

The client Flask app is a single-identity process (one machine, one JWT).
There is no browser session involved — the JWT represents the *machine*,
not a logged-in user.  A simple module-level variable is the clearest way
to hold this state for a PoC.

Usage:
    from client_app.client_state import state

    state.jwt_token = "eyJ..."        # set after login
    token = state.jwt_token           # retrieve for outgoing requests
    state.clear()                     # clear on logout
"""
from typing import Optional


class _ClientState:
    """Holds the runtime identity of this client node."""

    def __init__(self):
        self.jwt_token: Optional[str]  = None
        self.client_id: Optional[str]  = None
        self.server_url: Optional[str] = None
        self.username: Optional[str]   = None

    def clear(self) -> None:
        """Reset all state (e.g. on logout or re-login)."""
        self.jwt_token  = None
        self.username   = None
        # client_id and server_url are set at startup — don't clear those

    def is_authenticated(self) -> bool:
        return self.jwt_token is not None

    def auth_headers(self) -> dict:
        """Return headers dict with Bearer token for outgoing requests."""
        if not self.jwt_token:
            return {}
        return {"Authorization": f"Bearer {self.jwt_token}"}


# Singleton — import this anywhere in client_app
state = _ClientState()
