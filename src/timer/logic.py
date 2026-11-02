def format_time(seconds: int) -> str:
    minutes, secs = divmod(seconds, 60) if seconds >= 0 else (0, 0)
    return f"{minutes:02d}:{secs:02d}"


def format_duration(seconds: int) -> str:
    """A length of time in whole minutes: `25m`, `3h 05m`."""
    hours, minutes = divmod(seconds // 60, 60)
    if hours == 0:
        return f"{minutes}m"
    return f"{hours}h {minutes:02d}m"
