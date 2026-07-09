"""Modelo de datos: Project, Slide, Layer y subclases, con (de)serialización a dict."""

from dataclasses import dataclass, field, asdict
import uuid

from .constants import VERDE, BLANCO, BOX_COLOR, LOGO_FILE


DEFAULT_PHOTO_ADJUST = {
    "brightness": 1.0,
    "contrast": 1.0,
    "saturation": 1.0,
    "warmth": 0.0,
    "sharpness": 1.0,
    "shadows": 0.0,
    "vignette": 0.0,
}

DEFAULT_PHOTO_OVERLAY = {
    "bottom_grad": False,
    "top_grad": False,
    "strength": 0.0,
}

DEFAULT_FORMAT = {"name": "feed_4x5", "w": 1080, "h": 1350}


def _short_id() -> str:
    return uuid.uuid4().hex[:8]


def _photo_adjust_defaults() -> dict:
    return dict(DEFAULT_PHOTO_ADJUST)


def _photo_overlay_defaults() -> dict:
    return dict(DEFAULT_PHOTO_OVERLAY)


def _default_format() -> dict:
    return dict(DEFAULT_FORMAT)


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
    adjust: dict = field(default_factory=_photo_adjust_defaults)
    overlay: dict = field(default_factory=_photo_overlay_defaults)


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


@dataclass
class Slide:
    format: dict = field(default_factory=_default_format)
    layout_tag: str | None = None
    layers: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "format": dict(self.format),
            "layout_tag": self.layout_tag,
            "layers": [layer.to_dict() for layer in self.layers],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Slide":
        return cls(
            format=dict(data["format"]),
            layout_tag=data.get("layout_tag"),
            layers=[layer_from_dict(l) for l in data.get("layers", [])],
        )


@dataclass
class Project:
    version: int = 1
    name: str = "Proyecto sin título"
    default_format: dict = field(default_factory=_default_format)
    palette: dict = field(default_factory=lambda: {
        "verde": list(VERDE),
        "blanco": list(BLANCO),
        "box": list(BOX_COLOR),
    })
    shared: dict = field(default_factory=dict)
    slides: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "name": self.name,
            "default_format": dict(self.default_format),
            "palette": dict(self.palette),
            "shared": dict(self.shared),
            "slides": [slide.to_dict() for slide in self.slides],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        return cls(
            version=data.get("version", 1),
            name=data.get("name", "Proyecto sin título"),
            default_format=dict(data["default_format"]),
            palette=dict(data["palette"]),
            shared=dict(data.get("shared", {})),
            slides=[Slide.from_dict(s) for s in data.get("slides", [])],
        )


def crear_slide_por_defecto(
    photo_path: str = "",
    titulo: str = "Tu título aquí",
    subtitulo: str = "frase secundaria",
    descripcion: str = "",
    formato: dict | None = None,
) -> Slide:
    """Crea una lámina por defecto (foto + logo + título + subtítulo + caja)."""
    slide = Slide(format=dict(formato) if formato is not None else _default_format())
    slide.layers = [
        PhotoLayer(name="Foto", z=0, x=0.0, y=0.0, w=1.0, h=1.0,
                   src=photo_path, offset_x=0.5, offset_y=0.5),
        LogoLayer(name="Logo", z=1, x=0.40, y=0.022, w=0.20, h=0.20,
                  src=str(LOGO_FILE)),
        TextLayer(name="Título", z=2, x=0.055, y=0.42, role="title",
                  size=0.087, text=titulo),
        TextLayer(name="Subtítulo", z=3, x=0.50, y=0.55,
                  role="subtitle", size=0.050, text=subtitulo),
        BoxLayer(name="Descripción", z=4, x=0.05, y=0.808,
                 size=0.033, text=descripcion, icon="planta"),
    ]
    return slide


def crear_proyecto_por_defecto(photo_path: str = "") -> Project:
    """Crea el proyecto por defecto con una lámina de marca inicial."""
    project = Project()
    project.slides = [crear_slide_por_defecto(photo_path)]
    return project
