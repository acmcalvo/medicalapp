def redact_sensitive(value: str) -> str:
    return value[:2] + "***" if value else value
