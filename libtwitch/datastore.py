from __future__ import annotations
from enum import Enum, auto
from typing import Any, Union

from libtwitch import IrcChannel, IrcChatter

class DatastoreDomain(Enum):
  Global = auto() # TODO
  Channel = auto()
  Chatter = auto()

def get_domain(subject : Union[None, IrcChannel, IrcChatter]) -> DatastoreDomain:
  if subject is None:
    return DatastoreDomain.Global
  elif isinstance(subject, IrcChannel):
    return DatastoreDomain.Channel
  elif isinstance(subject, IrcChatter):
    return DatastoreDomain.Chatter
  else:
    print("Invalid subject type")
    return None

class Datastore:
  def get(self, subject : Union[None, IrcChannel, IrcChatter], key : str, fallback = None) -> Any:
    pass

  def set(self, subject : Union[None, IrcChannel, IrcChatter], key : str, value) -> None:
    pass

  def has(self, subject : Union[None, IrcChannel, IrcChatter], key : str) -> bool:
    pass

  def rem(self, subject : Union[None, IrcChannel, IrcChatter], key : str) -> None:
    pass

  def keys(self, subject : Union[None, IrcChannel, IrcChatter]) -> list[str]:
    pass

  def sync(self):
    pass
