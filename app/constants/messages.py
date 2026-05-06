"""Catálogo único de mensajes de error UI. Cero strings duplicados fuera de aquí."""

ERROR_MESSAGES: dict[str, str] = {
    "URL_NO_SOPORTADA": (
        "Plataforma no soportada. Pega un Reel, TikTok, Short, "
        "Facebook reel o video de X/Twitter."
    ),
    "URL_PROHIBIDA": "URL no permitida.",
    "DESCARGA_FALLIDA": (
        "No se pudo descargar el video. Verifica que sea publico y no este geobloqueado."
    ),
    "VIDEO_LARGO": "Video demasiado largo. Limite: 10 minutos.",
    "TRANSCRIPCION_NO_DISPONIBLE": (
        "Servicio de transcripcion no disponible. Intenta en unos minutos."
    ),
    "TIMEOUT_SUBPROCESO": "Una operacion tardo demasiado. Intenta nuevamente.",
    "TIMEOUT_TOTAL": (
        "La transcripcion excedio el tiempo maximo. Intenta con un video mas corto."
    ),
    "RATE_LIMIT_EXCEDIDO": "Demasiadas transcripciones. Espera un momento.",
    "INTENTOS_AUTH_EXCEDIDOS": "Demasiados intentos fallidos. Espera 1 hora.",
    "INPUT_DEMASIADO_GRANDE": "El formulario excede el tamano permitido.",
}
