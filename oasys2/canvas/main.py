"""
"""
import os
import sys
import logging
import pickle
import time

from orangecanvas import localization
from orangecanvas import utils, config

from orangecanvas.registry import WidgetRegistry
from orangecanvas.registry.qt import QtRegistryHandler
from orangecanvas.registry import cache

log = logging.getLogger(__name__)

from orangecanvas.main import Main as OrangeMain
from oasys2.canvas import config as oasysconfig

class Main(OrangeMain):
    def __init__(self):
        super(Main, self).__init__()

    def activate_default_config(self):
        """
        Activate the default configuration (:mod:`config`)
        """
        cfg = oasysconfig.Default()
        self.config = cfg
        config.set_default(cfg)
        # Init config
        config.init()

    def run_discovery(self) -> WidgetRegistry:
        """
        Run the widget discovery and return the resulting registry.
        """
        options = self.options
        language_changed = localization.language_changed()
        if not (options.force_discovery or language_changed):
            reg_cache = cache.registry_cache()
        else:
            reg_cache = None

        widget_registry = WidgetRegistry()
        handler = QtRegistryHandler(registry=widget_registry)
        handler.found_category.connect(
            lambda cd: self.show_splash_message(cd.name)
        )
        widget_discovery = self.config.widget_discovery(
            handler, cached_descriptions=reg_cache
        )

        if widget_discovery.cached_descriptions is None or len(widget_discovery.cached_descriptions.keys()) == 1:
            self.show_splash_message("Welcome to OASYS")

        cache_filename = os.path.join(config.cache_dir(), "widget-registry.pck")
        if options.no_discovery:
            with open(cache_filename, "rb") as f:
                widget_registry = pickle.load(f)
            widget_registry = WidgetRegistry(widget_registry)
        else:
            widget_discovery.run(self.config.widgets_entry_points())

            # Store cached descriptions
            cache.save_registry_cache(widget_discovery.cached_descriptions)
            with open(cache_filename, "wb") as f:
                pickle.dump(WidgetRegistry(widget_registry), f)
        self.registry = widget_registry
        if language_changed:
            localization.update_last_used_language()
        self.close_splash_screen()
        return widget_registry


def main(argv=None):
    return Main().run(argv)


if __name__ == "__main__":
    sys.exit(main())
