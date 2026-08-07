from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from trafilatura import bare_extraction

from .models import Article

USER_AGENT = "NERPrensa/0.1 (+GitHub Actions; entity extraction research)"


def _ensure_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("La URL debe usar http/https y contener un host válido.")

    host = parsed.hostname
    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise ValueError(f"No se pudo resolver el host: {host}") from exc

    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if any((ip.is_private, ip.is_loopback, ip.is_link_local, ip.is_multicast, ip.is_reserved, ip.is_unspecified)):
            raise ValueError("La URL resuelve a una dirección no pública; solicitud bloqueada por seguridad.")


def fetch_article(url: str, timeout: float = 25.0) -> Article:
    _ensure_public_url(url)
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "es-CL,es;q=0.9,en;q=0.5"}
    with httpx.Client(follow_redirects=True, timeout=timeout, headers=headers) as client:
        resp = client.get(url)
        resp.raise_for_status()
        final_url = str(resp.url)
        _ensure_public_url(final_url)
        html = resp.text

    doc = bare_extraction(
        html,
        url=final_url,
        with_metadata=True,
        include_comments=False,
        include_tables=False,
        favor_precision=True,
    )

    data = doc.as_dict() if doc else {}
    text = (data.get("text") or "").strip()
    if not text:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = "\n".join(p.get_text(" ", strip=True) for p in soup.find_all("p") if p.get_text(strip=True))

    if len(text) < 180:
        raise ValueError("No se pudo extraer suficiente texto del artículo. El medio puede requerir JavaScript, login o tener paywall.")

    return Article(
        url=final_url,
        title=(data.get("title") or "").strip(),
        author=(data.get("author") or "").strip(),
        date=str(data.get("date") or "").strip(),
        site_name=(data.get("sitename") or data.get("hostname") or "").strip(),
        text=text,
    )
