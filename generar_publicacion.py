"""
Generador de Publicaciones — Cabañas Don Cristobal.

Lanzador delgado: instala Pillow si falta e inicia la aplicación.
El editor vive en el paquete dcpub/.
"""

import sys

try:
    import PIL  # noqa: F401
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow", "-q"])

from dcpub.app import App

if __name__ == "__main__":
    App().mainloop()
