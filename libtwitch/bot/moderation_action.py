from __future__ import annotations

from functools import total_ordering

import libtwitch

@total_ordering
class ModerationAction:
  def __init__(self, action : libtwitch.ModerationActionType, duration : int = 0, reason : str = None, response : str = None):
    self.action : libtwitch.ModerationActionType = action
    self.reason : str = reason
    self.response : str = response
    self.duration : int = duration

  def __eq__(self, other : ModerationAction) -> bool:
    if self.action == other.action:
      if self.action == libtwitch.ModerationActionType.Timeout:
        return self.duration == other.duration
      return True
    return False

  def __ne__(self, other : ModerationAction) -> bool:
    return not (self == other)

  def __lt__(self, other : ModerationAction) -> bool:
    if self.action < other.action:
      return True

    if self.action == other.action and self.action == libtwitch.ModerationActionType.Timeout:
      if self.duration < other.duration:
        return True

    if self.reason is None and other.reason is not None:
      return True

    if self.response is None and other.response is not None:
      return True

    return False