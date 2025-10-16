import logging
import importlib_metadata
import importlib_resources
import pkgutil
import packaging.version

from AnyQt.QtGui import QImage, QPixmap, QFont, QFontMetrics, QColor, QPainter, QIcon
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

class OasysConfig(config.Default):
    OrganizationDomain = ""
    ApplicationName    = "OASYS2"
    ApplicationVersion = "2.0"

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

        size = 30 if len(version) < 5 else 16
        font = QFont()
        font.setPixelSize(size)
        font.setBold(True)
        font.setItalic(True)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 2)
        metrics = QFontMetrics(font)
        br = metrics.boundingRect(version).adjusted(-5, 0, 5, 0)
        br.moveCenter(QPoint(810, 277))

        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setFont(font)

        glow_color = QColor(255, 160, 122)  # salmon glow
        base_color = QColor("#8c0d8c")
        for i in range(2): # Draw multiple blurred layers
            alpha = int(255 * (1 - i / 5)) # Decrease opacity for outer layers
            offset = i  # Small offset for blur effect
            p.setPen(QColor(glow_color.red(), glow_color.green(), glow_color.blue(), alpha))
            p.setPen(QColor(glow_color.red(), glow_color.green(), glow_color.blue(), alpha))
            p.drawText(br.translated(offset, offset), Qt.AlignCenter, version)
            p.drawText(br.translated(-offset, offset), Qt.AlignCenter, version)
            p.drawText(br.translated(offset, -offset), Qt.AlignCenter, version)
            p.drawText(br.translated(-offset, -offset), Qt.AlignCenter, version)

        p.setPen(base_color)
        p.drawText(br, Qt.AlignCenter, version)
        p.end()

        #textarea = QRect(15, 15, 170, 20)
        textarea = QRect(30, 510, 500, 20)

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
