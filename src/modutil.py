import random
from datetime import datetime
from typing import Union

from libtwitch import Bot, IrcChatter, ModerationAction, ModerationActionType
from src import textutil

class ModerationMeta:
  def __init__(self, chatter : IrcChatter, mod : str, count : int, last : datetime):
    self.chatter : IrcChatter = chatter
    self.mod : str = mod
    self.count : int = count
    self.last : datetime = last

  def invoke(self):
    self.count += 1
    self.last = datetime.now()

  def save(self, bot : Bot):
    set_moderation_meta(bot, self.chatter, self.mod, self)

def get_moderation_meta(bot : Bot, chatter : IrcChatter, mod : str) -> ModerationMeta:
  count = bot.datastore.get(chatter, "mod.%s.count" % mod, 0)
  time = bot.datastore.get(chatter, "mod.%s.time" % mod, 0)

  return ModerationMeta(chatter, mod, count, datetime.fromtimestamp(time))

def set_moderation_meta(bot : Bot, chatter : IrcChatter, mod : str, meta : ModerationMeta) -> None:
  bot.datastore.set(chatter, "mod.%s.count" % mod, meta.count)
  bot.datastore.set(chatter, "mod.%s.time" % mod, datetime.timestamp(meta.last))

def get_tiered_moderation_action(chatter : IrcChatter, actions : dict, count : int = 1) -> Union[None, ModerationAction]:
  moderation_action = ModerationAction(ModerationActionType.Nothing)
  best = None
  for action in actions:
    if best is None or count >= action["count"] > best["count"]:
      best = action
  if best is None:
    return moderation_action

  relative_count = count - best["count"]

  mod_action = best["mod_action"]
  mod_action_type = mod_action["type"]

  # Get appropriate moderation action
  if "reason" in mod_action:
    moderation_action.reason = mod_action["reason"]

  if mod_action_type == "nothing":
    pass # Nothing to do
  elif mod_action_type == "remove_message":
    moderation_action.action = ModerationActionType.RemoveMessage
  elif mod_action_type == "timeout":
    # Calculate timeout duration
    # t = a*x^2 + b*x + c
    constant = 600
    if "constant" in mod_action:
      constant = mod_action["constant"]
    linear = 0
    if "linear" in mod_action:
      linear = mod_action["linear"]
    quadratic = 0
    if "quadratic" in mod_action:
      quadratic = mod_action["quadratic"]
    duration = (quadratic * relative_count * relative_count) + (linear * relative_count) + constant

    moderation_action.action = ModerationActionType.Timeout
    moderation_action.duration = duration
  elif mod_action_type == "ban":
    moderation_action.action = ModerationActionType.Ban
  else:
    print("Unknown mod action: %s" % mod_action_type)

  if len(best["messages"]) > 0:
    text = random.choice(best["messages"])
    data = {
      "user.name": chatter.name,
      "count": count,
      "duration": moderation_action.duration
    }
    moderation_action.response = textutil.substitute_variables(text, data)

  return moderation_action