"""Local-only PySide6 host for built Vue/Vuetify assets."""

from __future__ import annotations

from pathlib import Path
import sys

from PySide6.QtCore import QUrl
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineUrlRequestInterceptor,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QMainWindow

from jarvis.desktop.bridge import JarvisBridge


class LocalOnlyRequests(QWebEngineUrlRequestInterceptor):
    def __init__(self, assets_root: Path, parent=None):
        super().__init__(parent)
        self.assets_root = assets_root.resolve()

    def interceptRequest(self, info) -> None:
        url = info.requestUrl()
        scheme = url.scheme().lower()
        if scheme == "file":
            path = Path(url.toLocalFile()).resolve()
            if path != self.assets_root and self.assets_root not in path.parents:
                info.block(True)
        elif scheme not in {"qrc", "data", "blob", "about"}:
            info.block(True)


class LocalOnlyPage(QWebEnginePage):
    def __init__(self, profile: QWebEngineProfile, entry: Path, parent=None):
        super().__init__(profile, parent)
        self.entry = entry.resolve()

    def acceptNavigationRequest(self, url, navigation_type, is_main_frame):
        if is_main_frame:
            return url.scheme() == "file" and Path(url.toLocalFile()).resolve() == self.entry
        return super().acceptNavigationRequest(url, navigation_type, is_main_frame)


class JarvisWindow(QMainWindow):
    def __init__(self, assets_root: Path):
        super().__init__()
        self.setWindowTitle("JARVIS · TB-01")
        self.resize(1280, 820)
        self._bridge = JarvisBridge(self)
        self._bridge.attach_window(self)
        self._profile = QWebEngineProfile(self)  # off-the-record profile
        self._interceptor = LocalOnlyRequests(assets_root, self)
        self._profile.setUrlRequestInterceptor(self._interceptor)
        self._view = QWebEngineView(self)
        self._page = LocalOnlyPage(self._profile, assets_root / "index.html", self._view)
        self._view.setPage(self._page)
        self._channel = QWebChannel(self._page)
        self._channel.registerObject("jarvis", self._bridge)
        self._page.setWebChannel(self._channel)
        self.setCentralWidget(self._view)
        self._view.setUrl(QUrl.fromLocalFile(str(assets_root / "index.html")))

    def closeEvent(self, event):
        if self._bridge.active:
            self._bridge.request_shutdown()
            event.ignore()
            self.setWindowTitle("JARVIS · encerrando resposta…")
            return
        super().closeEvent(event)


def launch_desktop() -> int:
    project_root = Path(__file__).resolve().parents[3]
    assets_root = project_root / "frontend" / "dist"
    if not (assets_root / "index.html").is_file():
        print("Frontend não compilado: execute 'npm install' e 'npm run build' em frontend/.",
              file=sys.stderr)
        return 2
    app = QApplication.instance() or QApplication(sys.argv)
    window = JarvisWindow(assets_root)
    window.show()
    return app.exec()
