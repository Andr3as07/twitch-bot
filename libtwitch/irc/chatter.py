from __future__ import annotations

from typing import Optional

import libtwitch
from libtwitch import ChatterType

class IrcChatter:
  def __init__(self, channel : libtwitch.IrcChannel, name : str):
    self.channel : libtwitch.IrcChannel = channel
    self.name : str = name
    self._display : Optional[str] = None
    self.id : Optional[int] = None
    self.type : ChatterType = ChatterType.Unknown

  def has_type(self, other : ChatterType) -> bool:
    return (int(self.type) & ~other) != 0

  @property
  def display_name(self) -> str:
    if self._display is not None:
      return self._display
    return self.name

  def timeout(self, duration : int, reason : str = None):
    self.channel.timeout(self, duration, reason)

  def ban(self, reason : str = None):
    self.channel.ban(self, reason)

  def __str__(self):
    return "%s#%s(%s)" % (self.display_name, self.id, self.type)

  def __repr__(self):
    return str(self)
