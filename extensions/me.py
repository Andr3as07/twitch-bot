import io
import json
import os
from typing import Optional

from libtwitch import Bot, BotMessage, ModerationAction, Plugin
from src import modutil, pluginutil

class ModMe(Plugin):
  name = "mod.me"
  def __init__(self, bot):
    super().__init__(bot)
    self.config = None

  def on_load(self):
    self.config = pluginutil.load_config(self, {
      "actions": [
        {
          "count": 1,
          "messages": [
            "@{user.name} -> /me is not allowed."
          ],
          "mod_action": {
            "type": "timeout",
            "reason": "Using the /me command",
            "constant": 10
          }
        }
      ]
    })

  @staticmethod
  def _on_moderate_impl(message : BotMessage) -> bool:
    return message.text.startswith('ACTION ') and message.text.endswith('')

  def on_moderate(self, message : BotMessage) -> Optional[ModerationAction]:
    if not self._on_moderate_impl(message):
      return None

    meta = modutil.get_moderation_meta(self.bot, message.author, 'me')
    meta.invoke()
    meta.save(self.bot)
    action = modutil.get_tiered_moderation_action(message.author, self.config['actions'], meta.count)
    return action

def setup(bot : Bot):
  bot.register_plugin(ModMe(bot))

def teardown(bot : Bot):
  bot.unregister_plugin("mod.me")