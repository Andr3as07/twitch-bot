from __future__ import annotations
from typing import Any, Optional, Union

import libtwitch

DatastoreDomainType = Optional[Union[libtwitch.IrcChannel, libtwitch.IrcChatter]]

class Datastore:
  def get(self, subject : DatastoreDomainType, key : str, fallback = None) -> Any:
    pass

  def set(self, subject : DatastoreDomainType, key : str, value) -> None:
    pass

  def has(self, subject : DatastoreDomainType, key : str) -> bool:
    pass

  def rem(self, subject : DatastoreDomainType, key : str) -> None:
    pass

  def keys(self, subject : DatastoreDomainType) -> list[str]:
    pass

  def sync(self):
    pass

  @staticmethod
  def _get_domain(subject: DatastoreDomainType) -> libtwitch.DatastoreDomain:
    if subject is None:
      return libtwitch.DatastoreDomain.Global
    elif isinstance(subject, libtwitch.IrcChannel):
      return libtwitch.DatastoreDomain.Channel
    elif isinstance(subject, libtwitch.IrcChatter):
      return libtwitch.DatastoreDomain.Chatter
    else:
      print("Invalid subject type")
      return None
