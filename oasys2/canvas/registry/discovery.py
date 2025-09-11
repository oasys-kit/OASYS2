import pkgutil
import inspect
import logging

from orangecanvas.registry import discovery

from oasys2.canvas.menus.menu import OMenu

log = logging.getLogger(__name__)

class MenuRegistry(object):

    def __init__(self, menus=None):
        self.registry = menus if menus is not None else []

    def menus(self):
        return self.registry

    def addMenu(self, menu):
        self.registry.append(menu)


def omenus_from_package(package):
    try:
        package = discovery.asmodule(package)
    except ImportError:
        return
    for path in package.__path__:
        for _, mod_name, ispkg in pkgutil.iter_modules([path]):
            if ispkg:
                continue

            name = package.__name__ + "." + mod_name
            try:
                menu_module = discovery.asmodule(name)
            except ImportError:
                log.error("Error importing '%s'", name, exc_info=True)
                return

            for name, menu_class in inspect.getmembers(menu_module):
                if inspect.isclass(menu_class) and \
                        issubclass(menu_class, OMenu) and not name == "OMenu":
                    try:
                        yield menu_class()
                    except Exception:
                        log.error("Error creating menu instance from '%s'",
                                  menu_class, exc_info=True)
