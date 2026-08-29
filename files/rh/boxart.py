# -*- coding: utf-8 -*-
"""Chinh sach boxart: URL nao la bia that, URL nao chi la anh "chua co bia".

Nha cung cap khong tra 404 khi thieu bia - ho tra 200 kem mot anh placeholder.
Kho catalogue vi the co 23.931 dong tro vao no-image.png cua retrostic (may anh
gach cheo 245x165, 8 KB) va 20 dong placeholder cua gametuoitho. Tai chung ve la
tai ve mot anh 404, ghi len the, roi ve de len tile avatar tu ve cua RetroHub -
cai tile it ra con cho biet ten game va he may.
"""

# Khop theo ten file cuoi duong dan, khong khop chuoi con: retrostic co mot bia
# that ten "better-default-text-boxes.png" (ban hack sua khung thoai), va khop
# chuoi con "default" se giet nham no.
PLACEHOLDER_BASENAMES = frozenset((
    "no-image.png",      # retrostic, 23.931 dong
    "placeholder.png",   # gametuoitho
    "placeholder.svg",   # gametuoitho
    "default.jpg",       # dieu kien cu trong app.py, giu lai
))

def is_real_boxart_url(url):
    """True khi url dang tro toi mot tam bia that, dang tai duoc."""
    if not url:
        return False
    url = str(url).strip()
    if not url or url == "null" or not url.lower().startswith("http"):
        return False
    # Bo query va fragment truoc khi lay ten file: "no-image.png?v=2" van la
    # placeholder.
    path = url.split("#", 1)[0].split("?", 1)[0]
    return path.rsplit("/", 1)[-1].lower() not in PLACEHOLDER_BASENAMES
