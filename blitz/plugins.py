__author__ = 'Will Hart'

import logging

import blitz.communications.signals as sigs


class PluginMount(type):
    """
    A plugin mount point derived from:
        http://djangosnippets.org/snippets/542/
    """

    logger = logging.getLogger(__name__)
    plugins = []

    def __init__(cls, name, bases, attrs):
        super(PluginMount, cls).__init__(name, bases, attrs)

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
            cls.logger.debug("Registered signals for plugin %s" % instance.description)
        except AttributeError:
            cls.logger.debug("No signals to register for plugin %s" % instance.description)

        # fire the connected signal
        sigs.plugin_loaded.send(instance)
        cls.logger.debug("Finished loading plugin: %s" % instance.description)

    @classmethod
    def get_plugin(cls, plugin_type):
        """
        Gets a plugin from the plugin list mathing the given type

        :parma plugin_type: the type of plugin obtained by `type(plugin)`

        :returns: The plugin matching the given type
        """
        for x in cls.plugins:
            if type(x) == plugin_type:
                return x

        return None


class Plugin(object):
    """
    All plugins (e.g. Expansion Boards or handlers) must be derived from this class
    They can be registered against blitz.signals by providing a register_signals function
    """
    __metaclass__ = PluginMount
    do_not_register = False

    def __init__(self, description="Default Plugin"):
        """
        Plugin instances MUST provide a description in the plugin constructor
        """
        self.description = description
