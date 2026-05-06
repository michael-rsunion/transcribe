from app.constants.messages import ERROR_MESSAGES

REQUIRED_KEYS = {
    "URL_NO_SOPORTADA",
    "URL_PROHIBIDA",
    "DESCARGA_FALLIDA",
    "VIDEO_LARGO",
    "TRANSCRIPCION_NO_DISPONIBLE",
    "TIMEOUT_SUBPROCESO",
    "TIMEOUT_TOTAL",
    "RATE_LIMIT_EXCEDIDO",
    "INTENTOS_AUTH_EXCEDIDOS",
    "INPUT_DEMASIADO_GRANDE",
}


def test_all_required_keys_present():
    assert REQUIRED_KEYS.issubset(ERROR_MESSAGES.keys())


def test_no_empty_messages():
    for key, value in ERROR_MESSAGES.items():
        assert value and isinstance(value, str), f"{key} debe ser string no vacio"
