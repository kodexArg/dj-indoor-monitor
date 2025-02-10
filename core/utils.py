from datetime import timedelta

TIMEFRAME_MAP = {
    '5S': '5S',
    '1T': '1min',
    '30T': '30min',
    '1H': '1h',
    '4H': '4h',
    '1D': '1D'
}

def get_timedelta_from_timeframe(timeframe):
    """
    Convierte un timeframe en su timedelta correspondiente.
    """
    time_windows = {
        '5S': timedelta(minutes=15),
        '1T': timedelta(hours=3),
        '30T': timedelta(hours=36),
        '1H': timedelta(days=3),
        '4H': timedelta(days=12),
        '1D': timedelta(days=42)
    }
    return time_windows[timeframe.upper()]

def get_start_date(timeframe, end_date):
    """
    Calcula la fecha de inicio restando el timedelta correspondiente a la fecha final.
    """
    return end_date - get_timedelta_from_timeframe(timeframe)

def to_bool(value):
    """
    Convierte un valor a booleano.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        value = value.lower()
        if value in ('true', '1', 't', 'y', 'yes'):
            return True
        elif value in ('false', '0', 'f', 'n', 'no'):
            return False
    if isinstance(value, int):
        return bool(value)
    return False