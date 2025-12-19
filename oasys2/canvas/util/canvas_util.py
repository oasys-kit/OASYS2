import sys
import inspect

from AnyQt.QtWidgets import QDialogButtonBox, QDialog, QVBoxLayout, QLabel, QTextEdit, QScrollArea
from AnyQt.QtCore import Qt

from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import (
    QColor,
    QBrush,
    QPen,
    QPainter,
    QPainterPath,
    QLinearGradient,
)


def draw_3D_text(
    painter: QPainter,
    x: float,
    y: float,
    text: str,
    font,
    *,
    # Look & feel
    top_color: QColor | str = "#FFF4D6",
    bottom_color: QColor | str = "#FF9F43",
    outline_color: QColor | str = "#2B1B10",
    outline_width: float = 3.0,
    highlight_color: QColor | str = "#FFFFFF",
    highlight_alpha: int = 90,
    # Depth / 3D
    depth: int = 7,
    depth_dx: float = 1.0,
    depth_dy: float = 1.0,
    depth_color: QColor | str = "#8A4B2A",
    depth_fade: bool = True,
    # Shadow
    shadow_dx: float = 4.0,
    shadow_dy: float = 4.0,
    shadow_color: QColor | str = "#000000",
    shadow_alpha: int = 110,
    shadow_layers: int = 6,
    # Rendering
    antialias: bool = True,
    return_bounds: bool = False,
):
    """
    Drop-in Disney-style 3D text renderer for PyQt6 QPainter.

    - Uses QPainterPath (clean vector edges)
    - Soft-ish shadow via layered fills (no QGraphicsEffect needed)
    - 3D extrusion via repeated offset fills
    - Warm gradient face + outline + subtle highlight

    Coordinates:
        (x, y) is the *baseline* position, like QPainter.drawText(x, y, text).

    Returns:
        If return_bounds=True, returns QRectF of the painted path (face bounds).
        Otherwise returns None.
    """

    def _qc(c: QColor | str) -> QColor:
        return c if isinstance(c, QColor) else QColor(c)

    top_c = _qc(top_color)
    bottom_c = _qc(bottom_color)
    out_c = _qc(outline_color)
    depth_c = _qc(depth_color)
    sh_c = _qc(shadow_color)
    hi_c = _qc(highlight_color)

    # Optional AA
    if antialias:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    else:
        painter.save()

    painter.setFont(font)

    # Build text as a vector path (best quality)
    path = QPainterPath()
    path.addText(QPointF(x, y), font, text)
    bounds = path.boundingRect()

    # ---------- Shadow (layered for softness) ----------
    # We "fake blur" by drawing multiple slightly shifted translucent layers.
    # shadow_layers=0 disables.
    if shadow_layers > 0 and (shadow_alpha > 0):
        base_alpha = max(0, min(255, shadow_alpha))
        for i in range(shadow_layers, 0, -1):
            t = i / shadow_layers  # 0..1
            a = int(base_alpha * (t * t))  # stronger near the text
            col = QColor(sh_c)
            col.setAlpha(a)

            dx = shadow_dx * (1.0 + (i - 1) * 0.20)
            dy = shadow_dy * (1.0 + (i - 1) * 0.20)
            painter.save()
            painter.translate(dx, dy)
            painter.fillPath(path, col)
            painter.restore()

    # ---------- 3D extrusion (depth) ----------
    # Draw "back" layers behind the face.
    if depth > 0:
        for i in range(depth, 0, -1):
            t = i / max(1, depth)  # 0..1
            col = QColor(depth_c)
            if depth_fade:
                # Fade slightly as it goes "back"
                col.setAlpha(int(220 * (0.35 + 0.65 * t)))
            painter.save()
            painter.translate(depth_dx * i, depth_dy * i)
            painter.fillPath(path, col)
            painter.restore()

    # ---------- Face gradient ----------
    # Gradient along the text's vertical bounds.
    grad = QLinearGradient(bounds.left(), bounds.top(), bounds.left(), bounds.bottom())
    grad.setColorAt(0.0, top_c)
    grad.setColorAt(1.0, bottom_c)

    painter.fillPath(path, QBrush(grad))

    # ---------- Outline ----------
    if outline_width > 0:
        pen = QPen(out_c, float(outline_width))
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

    # ---------- Subtle highlight (top-left “sheen”) ----------
    if highlight_alpha > 0:
        col = QColor(hi_c)
        col.setAlpha(max(0, min(255, highlight_alpha)))
        pen = QPen(col, max(1.0, outline_width * 0.35))
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.save()
        painter.translate(-outline_width * 0.25, -outline_width * 0.35)
        painter.drawPath(path)
        painter.restore()

    painter.restore()

    return bounds if return_bounds else None



def add_widget_parameters_to_module(module_name):
    module             = sys.modules[module_name]
    oasys_widget_class = getattr(sys.modules["oasys2.widget.widget"], "OWWidget")
    widget_class       = None

    for _, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and obj.__module__ == module_name:
            if issubclass(obj, oasys_widget_class):
                widget_class = obj
                break

    if not widget_class is None:
        setattr(module, "WIDGET_CLASS", widget_class.__qualname__)
        try: setattr(module, "NAME", widget_class.name)
        except: print(f"no NAME for {module_name}.{widget_class}")
        try: setattr(module, "DESCRIPTION", widget_class.description)
        except: print(f"no DESCRIPTION for {module_name}.{widget_class}")
        try: setattr(module, "ICON", widget_class.icon)
        except: print(f"no ICON for {module_name}.{widget_class}")
        try: setattr(module, "PRIORITY", widget_class.priority)
        except: print(f"no PRIORITY for {module_name}.{widget_class}")
        try: setattr(module, "INPUTS", [getattr(widget_class.Inputs, input) for input in widget_class.Inputs.__dict__ if not input.startswith("__")])
        except: print(f"no INPUTS for {module_name}.{widget_class}")
        try: setattr(module, "OUTPUTS", [getattr(widget_class.Outputs, output) for output in widget_class.Outputs.__dict__ if not output.startswith("__")])
        except: print(f"no OUTPUTS for {module_name}.{widget_class}")



try:
    class ShowTextDialog(QDialog):

        def __init__(self, title, text, width=650, height=400, parent=None, label=False, button=True):
            QDialog.__init__(self, parent)
            self.setModal(True)
            self.setWindowTitle(title)
            layout = QVBoxLayout(self)

            if label:
                text_area = QLabel(text)
            else:
                text_edit = QTextEdit("", self)
                text_edit.append(text)
                text_edit.setReadOnly(True)

                text_area = QScrollArea(self)
                text_area.setWidget(text_edit)
                text_area.setWidgetResizable(False)
                text_area.setFixedHeight(height)
                text_area.setFixedWidth(width)

            layout.addWidget(text_area)

            if button:
                bbox = QDialogButtonBox(QDialogButtonBox.Ok)
                bbox.accepted.connect(self.accept)
                layout.addWidget(bbox)

        @classmethod
        def show_text(cls, title, text, width=650, height=400, parent=None, label=False, button=True):
            dialog = ShowTextDialog(title, text, width, height, parent, label, button)
            dialog.show()

    class ShowWaitDialog(QDialog):
        def __init__(self, title, text, width=500, height=80, parent=None):
            QDialog.__init__(self, parent)
            self.setModal(True)
            self.setWindowTitle(title)
            layout = QVBoxLayout(self)
            self.setFixedWidth(width)
            self.setFixedHeight(height)
            label = QLabel()
            label.setFixedWidth(int(width*0.95))
            label.setText(text)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font: 14px")
            layout.addWidget(label)
            label = QLabel()
            label.setFixedWidth(int(width*0.95))
            label.setText("Please wait....")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font: bold italic 16px; color: rgb(232, 120, 32);")
            layout.addWidget(label)
except:
    pass