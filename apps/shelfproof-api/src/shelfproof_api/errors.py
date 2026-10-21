class Conflict(ValueError):
    """Current state, binding or allowance does not authorize this operation."""


class Forbidden(ValueError):
    """Indistinguishable unavailable resource/permission denial."""
