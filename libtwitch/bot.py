import importlib
import sys
from typing import Any

import libtwitch
from libtwitch.datastore import Datastore

class Bot(libtwitch.Connection):
  def __init__(self, nickname : str, token : str, store : Datastore):
    super().__init__(nickname, token)

    self.datastore = store

    self._extensions : dict[str, Any] = {}
    self.plugins : dict[str, libtwitch.Plugin] = {}

  def register_plugin(self, plugin : libtwitch.Plugin):
    if not isinstance(plugin, libtwitch.Plugin):
      return False # plugins must derive from Plugin

    name = plugin.get_name()
    self.plugins[name] = plugin
    plugin.on_event(libtwitch.PluginEvent.SelfLoad)

    for other_plugin_name in self.plugins: # Inform all other plugins
      if other_plugin_name == name:
        continue
      self._on_event(libtwitch.PluginEvent.PluginLoad, name) # Inform the cog of it's own loading

  def get_plugin(self, name : str):
    return self.plugins.get(name)

  def unregister_plugin(self, name : str):
    plugin = self.plugins.pop(name, None)
    if plugin is None:
      return

    plugin.on_event(libtwitch.PluginEvent.SelfUnload) # Inform the plugin of it's own unloading
    self._on_event(libtwitch.PluginEvent.PluginUnload, name) # Inform all other plugins

  def _on_event(self, event : libtwitch.PluginEvent, *args, **kwargs):
    for plugin_name in self.plugins:
      self.plugins[plugin_name].on_event(event, *args, **kwargs)

  def load_extension(self, path : str):
    path = "extensions." + path

    try:
      name = importlib.util.resolve_name(path, None)
    except ImportError:
      return False # Extension not found

    if name in self._extensions:
      return False # Already loaded

    spec = importlib.util.find_spec(name)
    if spec is None:
      return False # Extension not found

    lib = importlib.util.module_from_spec(spec)
    sys.modules[name] = lib
    try:
      spec.loader.exec_module(lib)
    except Exception as ex:
      del sys.modules[name]
      return False # Failed to load extension

    try:
      setup = getattr(lib, 'setup')
    except AttributeError:
      del sys.modules[name]
      return # Entry point not found

    try:
      setup(self)
    except Exception as ex:
      del sys.modules[name]
      # self._remove_module_references(lib.__name__)
      self._call_extension_finalizer(lib, name)
      return False # Error while calling extension entry point
    else:
      self._extensions[name] = lib

  def unload_extension(self, path):
    path = "extensions." + path

    try:
      name = importlib.util.resolve_name(path, None)
    except ImportError:
      return False # Extension not found

    lib = self._extensions.get(name)
    if lib is None:
      return False # Extension not loaded

    self._call_extension_finalizer(lib, name)

  def _call_extension_finalizer(self, lib, key):
    try:
      func = getattr(lib, 'teardown')
    except AttributeError:
      pass # We don't have a teardown function, that is ok
    else:
      try:
        func(self)
      except Exception:
        pass
    finally:
      self._extensions.pop(key, None)
      sys.modules.pop(key, None)
      name = lib.__name__
      for module in list(sys.modules.keys()):
        if name == module or module.startswith(name + "."):
          del sys.modules[module]

  def on_ready(self):
    pass

  def on_destruct(self):
    # Let the cogs know that the bot is being destroyed
    self._on_event(libtwitch.PluginEvent.Destruct)

    # Unload all extensions
    for extension in self._extensions:
      self.unload_extension(extension)

    # Unload all plugins
    # Note plugins should be unregistered in the extensions teardown function.
    for plugin_name in self._plugins:
      self.unregister_plugin(plugin_name)
    self.datastore.sync()

  def on_raw_ingress(self, data : str):
    self._on_event(libtwitch.PluginEvent.Message.RawIngress, data)

  def on_raw_egress(self, data : str):
    self._on_event(libtwitch.PluginEvent.Message.RawEgress, data)

  def on_error(self, error : str):
    self._on_event(libtwitch.PluginEvent.Message.Error, error)

  def on_unknown(self, data : str):
    self._on_event(libtwitch.PluginEvent.Message.Unknown, data)

  def on_connect(self):
    self._on_event(libtwitch.PluginEvent.Message.Connect)
    self.datastore.sync()

  def on_disconnect(self):
    self._on_event(libtwitch.PluginEvent.Message.Disconnect)
    self.datastore.sync()

  def on_channel_join(self, channel : libtwitch.Channel):
    self._on_event(libtwitch.PluginEvent.Message.ChannelJoin, channel)
    self.datastore.sync()

  def on_channel_part(self, channel : libtwitch.Channel):
    self._on_event(libtwitch.PluginEvent.Message.ChannelPart, channel)
    self.datastore.sync()

  def on_join(self, join_event : libtwitch.ChatEvent):
    self._on_event(libtwitch.PluginEvent.Message.ChatterJoin, join_event)
    self.datastore.sync()

  def on_part(self, part_event : libtwitch.ChatEvent):
    self._on_event(libtwitch.PluginEvent.Message.ChatterPart, part_event)
    self.datastore.sync()

  def _handle_command(self, msg : libtwitch.Message):
    if not msg.text.startswith('?'):
      return False

    args = msg.text.strip().split(' ')
    if len(args) == 0:
      return False
    elif len(args[0]) == 1:
      return False

    # The command name is up to the first space.
    # Anything after that is a space separated list of arguments
    cmd = args[0][1:]
    args.pop(0)

    self._on_event(libtwitch.PluginEvent.Command, msg, cmd, args)
    return True

  def _moderate(self, msg : libtwitch.Message):
    if msg.author.has_type(libtwitch.ChatterType.Broadcaster) or \
      msg.author.has_type(libtwitch.ChatterType.Twitch) or \
      msg.author.has_type(libtwitch.ChatterType.Moderator):
      return

    harshest_action = None
    for plugin_name in self.plugins:
      action = self.plugins[plugin_name].on_event(libtwitch.PluginEvent.Moderate, msg)
      if action is None:
        continue
      if harshest_action is None or action > harshest_action:
        harshest_action = action
    if harshest_action is not None:
      msg.moderation_action = harshest_action

  def on_message(self, msg : libtwitch.Message):
    self._on_event(libtwitch.PluginEvent.Message.Message, msg)

  def on_privmsg(self, msg : libtwitch.Message):
    # Ignore self (echo)
    if msg.author.name.strip().lower() == self.nickname:
      return

    self._moderate(msg)

    self._on_event(libtwitch.PluginEvent.Message.Privmsg, msg)

    # Handle command
    if not self._handle_command(msg):
      # This is a normal message
      self.on_message(msg)

    msg.invoke()
    resp = msg.get_response()
    if resp is not None:
      msg.channel.chat(resp)
    self.datastore.sync()

  def get_config_dir(self):
    return "./config"

  def get_data_dir(self):
    return "./data"