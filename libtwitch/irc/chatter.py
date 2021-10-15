from __future__ import annotations

from typing import Optional

import libtwitch
from libtwitch import ChatterType

class IrcChatter:
  def __init__(self, channel : libtwitch.IrcChannel, login : str):
    self._channel : libtwitch.IrcChannel = channel
    self._login : str = login
    self._display : Optional[str] = None
    self._id : Optional[int] = -1
    self._type : ChatterType = ChatterType.Unknown

  def has_type(self, other : ChatterType) -> bool:
    return (int(self._type) & other) != 0

  @property
  def id(self) -> Optional[int]:
    if self._id is None or self._id < 0:
      return None
    return self._id

  @property
  def login(self) -> str:
    return self._login

  @property
  def display_name(self) -> str:
    if self._display is not None:
      return self._display
    return self._login

  @property
  def channel(self) -> libtwitch.IrcChannel:
    return self._channel

  def timeout(self, duration : int, reason : str = None):
    self._channel.timeout(self, duration, reason)

  def ban(self, reason : str = None):
    self._channel.ban(self, reason)

  def __str__(self):
    return "%s@%s" % (self.login, self._channel)

  def __repr__(self):
    return "<Chatter login: %s, channel: %s" % (self._login, self._channel)
