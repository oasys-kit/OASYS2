"""
fab.py — Floating Action Button overlay for the OASYS canvas
=============================================================

FABInstaller.install(main_window)
  └─ Creates a FABButton as a direct child of CanvasMainWindow
  └─ Installs a _ResizeFilter event-filter on the main window to keep
     the button pinned to the bottom-right corner after any resize

FABButton (QPushButton)
  └─ Fixed 56×56 px, borderless, circular, with a pulsing glow ring
  └─ On click: toggles the AIAssistantPopup QDialog

The button is parented to CanvasMainWindow (not the QGraphicsView viewport)
so it survives workflow tab switches without any re-parenting logic.
"""

import logging

from AnyQt.QtCore import (
    Qt, QObject, QEvent, QSize, QTimer, QPoint, QPropertyAnimation,
    QEasingCurve, pyqtProperty
)
from AnyQt.QtGui import QPainter, QColor, QBrush, QPen, QFont, QRadialGradient
from AnyQt.QtWidgets import QApplication, QPushButton, QWidget

from .popup import AIAssistantPopup

log = logging.getLogger(__name__)

# Distance from the bottom-right corner of the central widget area
_MARGIN_RIGHT  = 24
_MARGIN_BOTTOM = 24
_BTN_SIZE      = 56        # px, diameter of the circular button


class _ResizeFilter(QObject):
    """
    Event-filter installed on CanvasMainWindow.
    Repositions the FAB whenever the window is resized or shown.
    """

    def __init__(self, fab: "FABButton", main_window: QWidget) -> None:
        super().__init__(main_window)
        self._fab = fab
        self._mw  = main_window

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj is self._mw and event.type() in (
            QEvent.Resize, QEvent.Show, QEvent.WindowActivate
        ):
            # Defer by one event-loop tick so Qt has updated geometry first
            QTimer.singleShot(0, self._reposition)
        return False   # never consume the event

    def _reposition(self) -> None:
        if self._fab is None or not self._mw:
            return
        cw = self._mw.centralWidget()
        if cw is None:
            return
        # Map bottom-right of central widget to main-window coordinates
        cw_rect  = cw.rect()
        origin   = cw.mapTo(self._mw, cw_rect.bottomRight())
        x = origin.x() - _BTN_SIZE - _MARGIN_RIGHT
        y = origin.y() - _BTN_SIZE - _MARGIN_BOTTOM
        self._fab.move(x, y)
        self._fab.raise_()


class FABButton(QPushButton):
    """
    Circular floating action button drawn entirely with QPainter.
    Animates a pulsing glow ring to invite interaction.
    """

    # Qt property used by QPropertyAnimation for the glow radius
    def _get_glow(self) -> float:
        return self._glow_radius

    def _set_glow(self, value: float) -> None:
        self._glow_radius = value
        self.update()

    glowRadius = pyqtProperty(float, _get_glow, _set_glow)

    def __init__(self, main_window: QWidget) -> None:
        super().__init__(main_window)
        self._popup   = None          # created lazily on first click
        self._glow_radius: float = 0.0

        self.setFixedSize(_BTN_SIZE, _BTN_SIZE)
        self.setFlat(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("OASYS AI Beamline Assistant")
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.SubWindow)
        self.raise_()

        # Pulsing glow animation (radius oscillates 0 → 12 → 0 px)
        self._anim = QPropertyAnimation(self, b"glowRadius", self)
        self._anim.setDuration(2400)
        self._anim.setStartValue(0.0)
        self._anim.setKeyValueAt(0.5, 12.0)
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.InOutSine)
        self._anim.setLoopCount(-1)   # forever
        self._anim.start()

        self.clicked.connect(self._on_clicked)
        self.show()

    # ── Drawing ──────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        r = min(cx, cy) - 2

        # Glow ring (animates)
        if self._glow_radius > 0:
            glow_r = r + self._glow_radius
            gpen = QPen(QColor(240, 160, 48, 80), self._glow_radius * 1.5)
            #gpen = QPen(QColor(56, 189, 248, 60), self._glow_radius * 1.5)
            p.setPen(gpen)
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(
                int(cx - glow_r), int(cy - glow_r),
                int(glow_r * 2), int(glow_r * 2),
            )

        # Outer border ring
        p.setPen(QPen(QColor(30, 90, 140), 1.5))
        p.setBrush(QBrush(QColor(255, 248, 235)))
        #p.setPen(QPen(QColor(180, 100, 20), 1.5))
        #p.setBrush(QBrush(QColor(4, 14, 32)))
        p.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))

        # Inner radial gradient fill (dark navy → slightly lighter)
        grad = QRadialGradient(cx, cy - r * 0.3, r * 1.2)
        grad.setColorAt(0.0, QColor(255, 245, 220))
        grad.setColorAt(1.0, QColor(240, 225, 195))
        #grad.setColorAt(0.0, QColor(12, 30, 60))
        #grad.setColorAt(1.0, QColor(4, 10, 24))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.NoPen)
        inner = r - 2
        p.drawEllipse(int(cx - inner), int(cy - inner),
                      int(inner * 2), int(inner * 2))

        # Beam-path icon: horizontal line + tilted mirror bar
        pen_beam = QPen(QColor(240, 160, 48), 2.0, Qt.SolidLine, Qt.RoundCap)
        #pen_beam = QPen(QColor(56, 189, 248), 2.0, Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen_beam)
        # Incoming beam (left half)
        p.drawLine(int(cx - r * 0.68), int(cy), int(cx - r * 0.08), int(cy))
        # Deflected beam (upper right)
        p.setPen(QPen(QColor(200, 80, 20), 2.0, Qt.SolidLine, Qt.RoundCap))
        #p.setPen(QPen(QColor(217, 119, 6), 2.0, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(int(cx + r * 0.08), int(cy), int(cx + r * 0.55), int(cy - r * 0.45))
        # Mirror element (tilted bar at 45°)
        p.setPen(QPen(QColor(120, 100, 80), 2.5, Qt.SolidLine, Qt.RoundCap))
        #p.setPen(QPen(QColor(148, 163, 184), 2.5, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(
            int(cx - r * 0.12), int(cy + r * 0.16),
            int(cx + r * 0.16), int(cy - r * 0.12),
        )
        # "AI" text badge (top-right quadrant)
        p.setPen(QColor(180, 90, 10))
        #p.setPen(QColor(56, 189, 248))
        font = QFont("Consolas", 12, QFont.Bold)
        p.setFont(font)
        p.drawText(int(cx + r * 0.18), int(cy - r * 0.30),
                   int(r * 0.75), int(r * 0.55),
                   Qt.AlignCenter, "AI")

    # ── Click ─────────────────────────────────────────────────────────────

    def _on_clicked(self) -> None:
        if self._popup is None:
            main_window = self.parentWidget()
            self._popup = AIAssistantPopup(parent=main_window)

        if self._popup.isVisible():
            self._popup.hide()
        else:
            self._reposition_popup()
            self._popup.show()
            self._popup.raise_()
            self._popup.activateWindow()

    def _reposition_popup(self) -> None:
        if self._popup is None:
            return
        # Anchor popup's bottom-right to just above the FAB
        btn_global = self.mapToGlobal(QPoint(self.width(), self.height()))
        pw = self._popup.width()
        ph = self._popup.height()
        x = btn_global.x() - pw
        y = btn_global.y() - ph - 8   # 8 px gap above the button

        # Keep entirely on screen
        screen = QApplication.primaryScreen().availableGeometry()
        x = max(screen.left() + 8, min(x, screen.right()  - pw - 8))
        y = max(screen.top()  + 8, min(y, screen.bottom() - ph - 8))

        self._popup.move(x, y)


class FABInstaller:
    """Singleton-style installer: called once from __init__.py."""

    _installed: bool = False

    @classmethod
    def install(cls, main_window: QWidget) -> None:
        if cls._installed:
            return
        cls._installed = True
        log.info("OASYS AI FAB: installing on %s", main_window)

        fab = FABButton(main_window)
        filt = _ResizeFilter(fab, main_window)
        main_window.installEventFilter(filt)

        # Initial position
        filt._reposition()
