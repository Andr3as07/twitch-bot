import io
import json
import os

from libtwitch import Bot, BotMessage, ModerationAction, Plugin
from src import modutil

class ModCaps(Plugin):
  name = "mod.caps"
  def __init__(self, bot):
    super().__init__(bot)
    self.config = None

  def on_load(self):
    config_path = self.get_config_dir() + "/config.json"
    if not os.path.exists(config_path):
      self.config = {
        "min": 10,
        "max": 50,
        "percent": 0.60,
        "actions": [
          {
            "count": 1,
            "messages": [
              "@{user.name} -> Stop spamming caps."
            ],
            "mod_action": {
              "type": "timeout",
              "reason": "Spamming Caps",
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
    num_caps = 0
    length = len(message.text)
    for char in message.text:
      if 'A' <= char <= 'Z':
        num_caps += 1

    if num_caps < self.config['min']:
      return False

    if num_caps > self.config['max']:
      return True

    if num_caps / length > self.config["percent"]:
      return True

    return False

  def on_moderate(self, message : IrcMessage) -> ModerationAction:
    if not self._on_moderate_impl(message):
      return None

    meta = modutil.get_moderation_meta(self.bot, message.author, 'caps')
    meta.invoke()
    meta.save(self.bot)
    action = modutil.get_tiered_moderation_action(message.author, self.config['actions'], meta.count)
    return action

def setup(bot : Bot):
  bot.register_plugin(ModCaps(bot))

def teardown(bot : Bot):
  bot.unregister_plugin("mod.caps")