from enum import Enum, auto

from libtwitch.core import Message

class CogEvent(Enum):
  Ready = auto()
  Destruct = auto()
  RawIngress = auto()
  RawEgress = auto()
  Error = auto()
  Connect = auto()
  Disconnect = auto()
  ChannelJoin = auto()
  ChannelPart = auto()
  ChatterJoin = auto()
  ChatterPart = auto()
  Message = auto()
  Command = auto()
  SelfLoad = auto()
  SelfUnload = auto()
  CogLoad = auto()
  CogUnload = auto()

class Cog:
  _commands = {}
  _listeners = {}

  @classmethod
  def command(cls, name):
    def decorator(func):
      cls._commands[name] = func
      return func
    return decorator

  def on_command(self, msg : Message, cmd : str, args : list[str]):
    if cmd in self._commands:
      self._commands[cmd](self, msg, args)
      return True
    return False

  @classmethod
  def listen(cls, event : CogEvent):
    def decorator(func):
      cls._listeners[event] = func
      return func
    return decorator

  def invoke(self, event : CogEvent, *args, **kwargs):
    if event in self._listeners:
      self._listeners[event](self, *args, **kwargs)