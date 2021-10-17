from enum import Enum, IntEnum, auto

class ModerationActionType(IntEnum):
  Nothing = 0
  RemoveMessage = 1
  Timeout = 2
  Ban = 3

class PluginEvent(Enum):
  # Bot events
  Destruct = auto()

  # IRC events
  RawIngress = auto()
  RawEgress = auto() # This is considered dangerous
  Connect = auto()
  Disconnect = auto()
  Error = auto() # TODO
  ErrorBaned = auto() # TODO
  ErrorTimedOut = auto() # TODO
  Unknown = auto()
  ChannelJoin = auto()
  ChannelPart = auto()
  ChatterJoin = auto()
  ChatterPart = auto()
  Moderate = auto()
  Privmsg = auto()
  Message = auto()
  Command = auto()
  Whisper = auto() # TODO
  RoomstateChange = auto()
  SubGift = auto() # TODO
  Raid = auto() # TODO
  Unraid = auto() # TODO
  Ritual = auto() # TODO
  BitsBadgeTier = auto() # TODO

  # Community events
  Bits = auto()
  Subscribe = auto()

  # Plugin events
  SelfLoad = auto()
  SelfUnload = auto()
  PluginLoad = auto()
  PluginUnload = auto()