__author__ = 'Will Hart'

import logging

import blitz.io.signals as signals


class PluginMount(type):

    logger = logging.getLogger(__name__)

    def __init__(cls, name, bases, attrs):
        if not hasattr(cls, 'plugins'):
            # This branch only executes when processing the mount point itself.
            # So, since this is a new plugin type, not an implementation, this
            # class shouldn't be registered as a plugin. Instead, it sets up a
            # list where plugins can be registered later.
            cls.plugins = []
        else:
            # This must be a plugin implementation, which should be registered.
            # Simply appending it to the list is all that's needed to keep
            # track of it later.
            cls.register_plugin(cls)

        # super(PluginMount, cls).__init__(name, bases, attrs)

    def register_plugin(cls, plugin):
        """
        Add the plugin to the plugin list and register it's signals
        """

        instance = plugin()

        # check if we should register this plugin
        if instance.do_not_register:
            cls.logger.debug("Skipping plugin %s due to do_not_register flag" % instance.description)
            return

        cls.plugins.append(instance)

        try:
            instance.register_signals()
        except AttributeError:
            pass

        # fire the connected signal
        signals.plugin_loaded(instance)

        cls.logger.debug("Loaded plugin: %s" % instance.description)


class Plugin(object):
    __metaclass__ = PluginMount

    def __init__(self, description):
        """
        Plugin instances MUST provide a description in the plugin constructor
        """
        self.description = description
