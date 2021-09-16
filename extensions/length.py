import io
import json
import os

from libtwitch import Bot, BotMessage, ModerationAction, Plugin
from src import modutil

class ModLength(Plugin):
  name = "mod.length"
  def __init__(self, bot):
    super().__init__(bot)
    self.config = None

  def on_load(self):
    config_path = self.get_config_dir() + "/config.json"
    if not os.path.exists(config_path):
      self.config = {
        "length": 300,
        "actions": [
          {
            "count": 1,
            "messages": [
              "@{user.name} -> Please no lengthy messages."
            ],
            "mod_action": {
              "type": "timeout",
              "reason": "Writing Long Paragraphs",
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

  def _on_moderate_impl(self, message : BotMessage) -> ModerationAction:
    length = self.config["length"]
    return len(message.text) > length

  def on_moderate(self, message : BotMessage) -> ModerationAction:
    if not self._on_moderate_impl(message):
      return None

    meta = modutil.get_moderation_meta(self.bot, message.author, 'length')
    meta.invoke()
    meta.save(self.bot)
    action = modutil.get_tiered_moderation_action(message.author, self.config['actions'], meta.count)
    return action

def setup(bot : Bot):
  bot.register_plugin(ModLength(bot))

def teardown(bot : Bot):
  bot.unregister_plugin("mod.length")