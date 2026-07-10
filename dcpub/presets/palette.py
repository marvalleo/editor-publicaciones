"""Paletas de marca disponibles para proyectos dcpub."""


PALETA_PRINCIPAL = {
    "id": "principal",
    "nombre": "Principal",
    "verde": [159, 184, 66],
    "verde_oliva": [111, 127, 50],
    "verde_profundo": [79, 94, 38],
    "blanco": [247, 241, 232],
    "box": [43, 30, 24, 158],
    "sombra": [20, 12, 8, 115],
}


PALETA_LEGACY = {
    "id": "legacy",
    "nombre": "Alternativo legacy",
    "verde": [141, 194, 111],      # v2.0 verde lima #8DC26F
    "blanco": [255, 255, 255],     # v2.0 white (puro)
    "box": [40, 25, 15, 215],      # v2.0 recuadro
}


PALETAS = {
    PALETA_PRINCIPAL["id"]: PALETA_PRINCIPAL,
    PALETA_LEGACY["id"]: PALETA_LEGACY,
}

