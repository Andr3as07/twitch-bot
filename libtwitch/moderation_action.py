from __future__ import annotations

from enum import IntEnum
from functools import total_ordering

class ModerationActionType(IntEnum):
  RemoveMessage = 0
  Timeout = 1
  Ban = 2


@total_ordering
class ModerationAction:
  def __init__(self, action : ModerationActionType, duration : int = 0, reason : str = None, response : str = None):
    self.action : ModerationActionType = action
    self.reason : str = reason
    self.response : str = response
    self.duration : int = duration

  def __eq__(self, other : ModerationAction) -> bool:
    if self.action == other.action:
      if self.action == ModerationActionType.Timeout:
        return self.duration == other.duration
      return True
    return False

  def __ne__(self, other : ModerationAction) -> bool:
    return not (self == other)

  def __lt__(self, other : ModerationAction) -> bool:
    if self.action < other.action:
      return True

    if self.action == other.action and self.action == ModerationActionType.Timeout:
      if self.duration < other.duration:
        return True

    if self.reason is None and other.reason is not None:
      return True

    if self.response is None and other.response is not None:
      return True

    return False