from __future__ import annotations

import time
from typing import Optional

import libtwitch

class IrcMessage:
  def __init__(self, channel : libtwitch.IrcChannel, author : libtwitch.IrcChatter, text : str, tags : dict[str, str]):
    self.timestamp : time = time.time()
    self.channel : libtwitch.IrcChannel = channel
    self.author : libtwitch.IrcChatter = author
    self.text : str = text
    self.tags : dict[str, str] = tags
    self.id : Optional[int] = None

  def delete(self) -> None:
    self.channel.chat(".delete %s" % self.id)
