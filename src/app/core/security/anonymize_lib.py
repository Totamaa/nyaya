def anonymize_ip(ip: str) -> str:
    parts = ip.split(".")
    if len(parts) == 4:
        parts[-1] = "x"
        anonymize_ip = ".".join(parts)
        return anonymize_ip
    return "unknown"

def anonymize_email(email: str) -> str:
    if "@" in email and "." in email.split("@")[-1]:
        local_part, domain = email.split("@")
        root = domain.split(".")[-1]
        anonymized_email = f"{local_part[0]}***{local_part[-1]}@{domain[0]}**.{root}"
        return anonymized_email
    return "unknown"