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
from jarvis.desktop.diagnostics import install_qt_diagnostics, trace


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
        self.setWindowTitle("JARVIS · TB-02")
        self.resize(1280, 820)
        self._bridge = JarvisBridge(self)
        self._bridge.attach_window(self)
        trace("window_construct_begin")
        self._profile = QWebEngineProfile(self)  # off-the-record profile
        self._interceptor = LocalOnlyRequests(assets_root, self)
        self._profile.setUrlRequestInterceptor(self._interceptor)
        self._view = QWebEngineView(self)
        self._view.renderProcessTerminated.connect(self._on_renderer_terminated)
        self._view.loadFinished.connect(self._on_view_loaded)
        self._page = LocalOnlyPage(self._profile, assets_root / "index.html", self._view)
        self._view.setPage(self._page)
        self._channel = QWebChannel(self._page)
        self._channel.registerObject("jarvis", self._bridge)
        self._page.setWebChannel(self._channel)
        self.setCentralWidget(self._view)
        self._view.setUrl(QUrl.fromLocalFile(str(assets_root / "index.html")))
        trace("window_construct_end")

    def _on_view_loaded(self, ok: bool) -> None:
        trace("webengine_load_finished", ok=bool(ok))

    def _on_renderer_terminated(self, status, exit_code: int) -> None:
        trace("webengine_renderer_terminated",
              status=str(getattr(status, "name", "unknown")),
              exit_code=int(exit_code))

    def closeEvent(self, event):
        trace("window_close_requested", worker_active=self._bridge.active)
        if self._bridge.active:
            self._bridge.request_shutdown()
            event.ignore()
            self.setWindowTitle("JARVIS · encerrando resposta…")
            trace("window_close_deferred")
            return
        trace("window_close_accepted")
        super().closeEvent(event)


def launch_desktop() -> int:
    project_root = Path(__file__).resolve().parents[3]
    assets_root = project_root / "frontend" / "dist"
    if not (assets_root / "index.html").is_file():
        print("Frontend não compilado: execute 'npm install' e 'npm run build' em frontend/.",
              file=sys.stderr)
        return 2
    install_qt_diagnostics()
    trace("desktop_launch")
    app = QApplication.instance() or QApplication(sys.argv)
    app.aboutToQuit.connect(lambda: trace("qt_about_to_quit"))
    window = JarvisWindow(assets_root)
    window.show()
    trace("qt_event_loop_enter")
    exit_code = app.exec()
    trace("qt_event_loop_exit", exit_code=int(exit_code))
    return exit_code
