import importlib
import sys

import libtwitch

class Bot(libtwitch.Connection):
  def __init__(self, nickname : str, token : str):
    super().__init__(nickname, token)

    self._extensions = {}
    self._cogs : dict[str, libtwitch.Cog] = {}

  def add_cog(self, name : str, cog : libtwitch.Cog):
    if not isinstance(cog, libtwitch.Cog):
      return False # cogs must derive from Cog

    self._cogs[name] = cog
    cog.invoke(libtwitch.CogEvent.SelfLoad)

    for other_cog_name in self._cogs: # Inform all other cogs
      if other_cog_name == name:
        continue
      self._cog_event(libtwitch.CogEvent.CogLoad, name) # Inform the cog of it's own loading

  def get_cog(self, name : str):
    return self._cogs.get(name)

  def remove_cog(self, name : str):
    cog = self._cogs.pop(name, None)
    if cog is None:
      return

    cog.invoke(libtwitch.CogEvent.SelfUnload) # Inform the cog of it's own unloading
    self._cog_event(libtwitch.CogEvent.CogUnload, name) # Inform all other cogs

  def _cog_event(self, event : libtwitch.CogEvent, *args, **kwargs):
    for cog in self._cogs:
      self._cogs[cog].invoke(event, *args, **kwargs)

  def load_extension(self, path):
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

  def unload_extension(self, path):
    try:
      name = importlib.util.resolve_name(path, None)
    except ImportError:
      return False # Extension not found

    lib = self._extensions.get(name)
    if lib is None:
      return False # Extension not loaded

    self._call_extension_finalizer(lib, name)

  def on_message(self, msg : libtwitch.Message):
    # Ignore self (echo)
    if msg.author.name.strip().lower() == self.nickname:
      return

    # Commands must start with this prefix
    if not msg.text.startswith('?'):
      return

    # Commands must contain at least the command name
    args = msg.text.strip().split(' ')
    if len(args) == 0:
      return
    elif len(args[0]) == 1:
      return

    # The command name is up to the first space.
    # Anything after that is a space separated list of arguments
    cmd = args[0][1:]
    args.pop(0)

    self.on_command(msg, cmd, args)

  def on_command(self, msg : libtwitch.Message, cmd : str, args : list[str]) -> None:
    for cog in self._cogs:
      if self._cogs[cog].on_command(msg, cmd, args):
        return True

    self._cog_event(libtwitch.CogEvent.Command, msg, cmd, args)
    return False

  def on_destruct(self):
    # Let the cogs know that the bot is being destroyed
    self._cog_event(libtwitch.CogEvent.Destruct)

    # Unload all extensions
    for extension in self._extensions:
      self.unload_extension(extension)