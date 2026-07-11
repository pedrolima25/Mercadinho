"""Geração de slugs de URL (ex: "Meu Mercado" -> "meu-mercado")."""

import re
import unicodedata


def slugify(texto: str, fallback: str = "item") -> str:
    """Converte um texto em um slug de URL."""
    texto = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^a-zA-Z0-9]+", "-", texto).strip("-").lower()
    return texto or fallback
