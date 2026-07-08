"""Modelo de datos: capas (Layer y subclases) con (de)serialización a dict."""

from dataclasses import dataclass, field, asdict
import uuid


def _short_id() -> str:
    return uuid.uuid4().hex[:8]


@dataclass
class Layer:
    id: str = field(default_factory=_short_id)
    name: str = ""
    type: str = "layer"
    visible: bool = True
    locked: bool = False
    z: int = 0
    x: float = 0.0
    y: float = 0.0
    w: float = 0.0
    h: float = 0.0
    rotation: float = 0.0
    opacity: float = 1.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PhotoLayer(Layer):
    type: str = "photo"
    src: str = ""
    fit: str = "cover"
    zoom: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0


@dataclass
class LogoLayer(Layer):
    type: str = "logo"
    src: str = ""
    keep_ratio: bool = True


@dataclass
class TextLayer(Layer):
    type: str = "text"
    text: str = ""
    role: str = "free"
    size: float = 0.05


@dataclass
class BoxLayer(Layer):
    type: str = "box"
    text: str = ""
    icon: str = "ninguno"
    size: float = 0.033


LAYER_CLASSES = {
    "photo": PhotoLayer,
    "logo": LogoLayer,
    "text": TextLayer,
    "box": BoxLayer,
}


def layer_from_dict(data: dict) -> Layer:
    """Reconstruye la subclase de Layer correcta según su campo "type"."""
    cls = LAYER_CLASSES[data["type"]]
    return cls(**data)
