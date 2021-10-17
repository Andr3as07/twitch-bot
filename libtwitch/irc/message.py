from __future__ import annotations

import time
import datetime
from typing import Optional

import libtwitch
from libtwitch.irc.events import MessageEvent, RaidEvent, SubEvent, SubGiftEvent

class IrcMessage:
  def __init__(self, channel : libtwitch.IrcChannel, author : libtwitch.IrcChatter, text : str, tags : dict[str, str]):
    self._timestamp : time = time.time() # TODO: Get timestamp form tags
    self._channel : libtwitch.IrcChannel = channel
    self._author : libtwitch.IrcChatter = author
    self._text : str = text
    self._tags : dict[str, str] = tags
    self._id : Optional[int] = -1
    self._event : Optional[MessageEvent] = None

  @property
  def is_sub(self) -> bool:
    return self._event is not None and isinstance(self._event, SubEvent)

  @property
  def is_raid(self) -> bool:
    return self._event is not None and isinstance(self._event, RaidEvent)

  @property
  def is_subgift(self) -> bool:
    return self._event is not None and isinstance(self._event, SubGiftEvent)

  @property
  def event(self) -> Optional[MessageEvent]:
    return self._event

  @property
  def id(self) -> Optional[int]:
    if self._id is None or self._id < 0:
      return None
    return self._id

  @property
  def tags(self) -> dict[str, str]:
    return self._tags

  @property
  def text(self) -> str:
    return self._text

  @property
  def author(self) -> libtwitch.IrcChatter:
    return self._author

  @property
  def channel(self) -> libtwitch.IrcChannel:
    return self._channel

  @property
  def timestamp(self) -> datetime.datetime:
    return datetime.datetime.utcfromtimestamp(int(self._timestamp) / 1000)

  def __str__(self):
    return self.text

  def __repr__(self):
    return "<Message author: %s, text: %s>" % (self._author, self.text)

  def delete(self) -> None:
    self.channel.chat(".delete %s" % self.id)
