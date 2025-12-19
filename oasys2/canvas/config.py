import logging
import importlib_metadata
import importlib_resources
import pkgutil
import packaging.version

from AnyQt.QtGui import QImage, QPixmap, QFont, QFontMetrics, QColor, QPainter, QIcon, QPen, QBrush, QLinearGradient
from AnyQt.QtCore import Qt, QCoreApplication, QPoint, QRect

from orangecanvas import config

from oasys2.canvas.registry import discovery
from oasys2.widget.workflow import widgetsscheme

WIDGETS_ENTRY = "oasys2.widgets"
MENU_ENTRY    = "oasys2.menus"
ADDONS_ENTRY  = "oasys2.addons"

#: Parameters for searching add-on packages in PyPi using xmlrpc api.
ADDON_PYPI_SEARCH_SPEC = {"keywords": "oasys2", "owner" : "lucarebuffi"}

# Add a default for our extra default-working-dir setting.
config.spec += [
    config.config_slot("output/default-working-dir", str, "", "Default working directory"),
    config.config_slot("oasys/addon-update-check-period", int, 1, "Check for updates every (in days)")
]

class Releases:
    ALPHA      = "Alpha"
    BETA       = "Beta"
    PRODUCTION = "Production"

class OasysConfig(config.Default):
    OrganizationDomain = ""
    ApplicationName    = "OASYS2"
    ApplicationVersion = "2.0"
    Release            = Releases.BETA

    @staticmethod
    def splash_screen():
        contents = pkgutil.get_data(__name__, "icons/oasys-splash-screen.png")
        img = QImage.fromData(contents, "png")
        pm = QPixmap.fromImage(img)
        version = QCoreApplication.applicationVersion()
        if version:
            version_parsed = packaging.version.Version(version)
            version_comp = version_parsed.release
            version = ".".join(map(str, version_comp[:2]))

        size = 60
        font = QFont()
        font.setPixelSize(size)
        font.setBold(True)
        font.setItalic(True)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 2)
        metrics = QFontMetrics(font)
        br = metrics.boundingRect(version).adjusted(-5, 0, 5, 0)
        br.moveCenter(QPoint(1002, 537))

        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setFont(font)

        # --- Convert QRect center alignment → baseline coordinates ---
        x = br.center().x() - metrics.horizontalAdvance(version) / 2
        y = br.center().y() + metrics.ascent() / 2

        from oasys2.canvas.util.canvas_util import draw_3D_text

        # --- Disney-style 3D text ---
        draw_3D_text(
            painter=p,
            x=x,
            y=y,
            text=version,
            font=font,
            top_color="#FFF4B9",  # lighter highlight
            bottom_color="#7D1520",  # your original color
            outline_color="FB7034", #"#361015",
            depth=4,
            depth_dx=1.2,
            depth_dy=1.2,
            outline_width=2,
            shadow_dx=1,
            shadow_dy=1,
        )

        p.end()

        if not OasysConfig.Release == Releases.PRODUCTION:
            size = 22
            font = QFont()
            font.setPixelSize(size)
            font.setBold(True)
            font.setItalic(True)
            font.setLetterSpacing(QFont.AbsoluteSpacing, 2)

            p = QPainter(pm)
            p.setRenderHint(QPainter.Antialiasing)
            p.setRenderHint(QPainter.TextAntialiasing)
            p.setFont(font)

            if OasysConfig.Release == Releases.ALPHA:
                text = (f"USER WARNING: {OasysConfig.Release} release. "
                        f"\nIt is distributed for testing purposes only.")
                p.setPen(QColor("#FFCCFF"))
            elif OasysConfig.Release == Releases.BETA:
                text = (f"USER WARNING: {OasysConfig.Release} release. "
                        f"\nIt is pre-production software, used it carefully.")
                p.setPen(QColor("#CAFA9A"))#"#CAFA9A")) #487A15

            metrics = QFontMetrics(font)
            br = metrics.boundingRect(text).adjusted(-5, -20, 5, 20)
            br.moveCenter(QPoint(500, 50))

            p.drawText(br, Qt.AlignLeft, text)
            p.end()

        textarea = QRect(30, 675, 500, 20)

        return pm, textarea

    @staticmethod
    def application_icon():
        """
        Return the main application icon.
        """
        ref = importlib_resources.files(__name__).joinpath("icons/oasys.png")
        with importlib_resources.as_file(ref) as path: return QIcon(str(path))

    @staticmethod
    def widgets_entry_points():
        return importlib_metadata.entry_points(group=WIDGETS_ENTRY)

    @staticmethod
    def addon_entry_points():
        return importlib_metadata.entry_points(group=ADDONS_ENTRY)

    @staticmethod
    def addon_pypi_search_spec():
        return dict(ADDON_PYPI_SEARCH_SPEC)

    @staticmethod
    def tutorials_entry_points():
        return importlib_metadata.entry_points(group="oasys.tutorials")

    workflow_constructor = widgetsscheme.OASYSWidgetsScheme


def omenus():
    """
    Return an iterator of oasys.menu.OMenu instances registered
    by 'orange.menu' pkg_resources entry point.
    """
    log = logging.getLogger(__name__)
    for ep in importlib_metadata.entry_points(group=MENU_ENTRY):
        try:
            menu = ep.load()
        except Exception:
            log.exception("Error loading a '%s' entry point.", MENU_ENTRY)
        else:
            if "MENU" in menu.__dict__:
                yield from discovery.omenus_from_package(menu)


def menu_registry():
    """
    Return the the OASYS extension menu registry.
    """
    return discovery.MenuRegistry(list(omenus()))
