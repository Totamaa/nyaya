from datetime import date


def subtract_months(d: date, n: int) -> date:
    month = d.month - n % 12
    year = d.year - n // 12
    if month <= 0:
        month += 12
        year -= 1
    return date(year, month, 1)


def month_range(limit: int, offset: int) -> tuple[date, date]:
    today = date.today()
    return subtract_months(today, offset + limit - 1), subtract_months(today, offset)
