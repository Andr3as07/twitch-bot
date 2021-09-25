from __future__ import annotations

from typing import Any, Optional

import libtwitch

class BotMessage(libtwitch.IrcMessage):
  @classmethod
  def from_raw_message(cls, msg : libtwitch.IrcMessage) -> BotMessage:
    return BotMessage(msg.channel, msg.author, msg.text, msg.tags)

  def __init__(self, channel : libtwitch.IrcChannel, author : libtwitch.IrcChatter, text : str, tags : dict[str, str]):
    super().__init__(channel, author, text, tags)

    self.response : Optional[str] = None
    self.moderation_action : Optional[libtwitch.ModerationAction] = None
    self.custom_data : dict[str, Any] = {}

  def get_response(self) -> str:
    if self.moderation_action is not None and self.moderation_action.response is not None:
      return self.moderation_action.response
    return self.response

  def invoke(self) -> None:
    from libtwitch import ModerationActionType

    if self.moderation_action is None:
      return

    action_type: ModerationActionType = self.moderation_action.action
    if action_type == ModerationActionType.RemoveMessage:
      self.delete()
    elif action_type == ModerationActionType.Timeout:
      self.author.timeout(self.moderation_action.duration, self.moderation_action.reason)
    elif action_type == ModerationActionType.Ban:
      self.author.ban(self.moderation_action.reason)
