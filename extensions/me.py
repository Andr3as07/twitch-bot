import io
import json
import os
import re

from libtwitch import Bot, BotMessage, ModerationAction, Plugin
from src import modutil

class ModMe(Plugin):
  name = "mod.me"
  def __init__(self, bot):
    super().__init__(bot)
    self.config = None

  def on_load(self):
    config_path = self.get_config_dir() + "/config.json"
    if not os.path.exists(config_path):
      self.config = {
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
      }
    else:
      with io.open(config_path) as f:
        jdata = json.load(f)
      if jdata is not None:
        self.config = jdata

  @staticmethod
  def _on_moderate_impl(message : BotMessage) -> ModerationAction:
    return message.text.startswith('ACTION ') and message.text.endswith('')

  def on_moderate(self, message : BotMessage) -> ModerationAction:
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