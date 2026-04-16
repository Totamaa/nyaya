import re

def normalize_first_name(value: str) -> str:
    value = re.sub(r"\s+", " ", value.strip())

    parts = re.split(r"([ -])", value)
    return "".join(part.capitalize() if part not in [" ", "-"] else part for part in parts)


def normalize_last_name(value: str) -> str:
    value = re.sub(r"\s+", " ", value.strip())

    parts = re.split(r"([ -])", value)
    return "".join(part.upper() if part not in [" ", "-"] else part for part in parts)


def normalize_email(value: str) -> str:
    return value.strip().lower()

def normalize_category(value: str) -> str:
    return value.strip().capitalize()

def normalize_title(value: str) -> str:
    return value.strip().title()
