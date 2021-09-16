import io
import json
import os
import re

from libtwitch import Bot, Message, ModerationAction, Plugin
from src import modutil

class ModLinks(Plugin):
  name = "mod.links"
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
              "@{user.name} -> No links please."
            ],
            "mod_action": {
              "type": "timeout",
              "reason": "Writing Links",
              "constant": 10
            }
          }
        ],
        "whitelist": []
      }
    else:
      with io.open(config_path) as f:
        jdata = json.load(f)
      if jdata is not None:
        self.config = jdata

  @staticmethod
  def _on_moderate_impl(message : Message) -> ModerationAction:
    # TODO: Allow specific domains and paths

    # findall() has been used with valid conditions for urls in string
    regex = r"((https?://)?(([^\s()<>]+)\.)*([a-z0-9\-.]+)\.([a-z]{2,})([^\s()<>?#]*)(?:\?([^\s()<>=#&]+=[^\s()<>=#&]*)(&([^\s()<>=#&]+=[^\s()<>=#&]*))*)?(?:#([^\s()<>]*))?)"
    urls = re.findall(regex, message.text, re.IGNORECASE)

    return len(urls) > 0

  def on_moderate(self, message : Message) -> ModerationAction:
    if not self._on_moderate_impl(message):
      return None

    meta = modutil.get_moderation_meta(self.bot, message.author, 'links')
    meta.invoke()
    meta.save(self.bot)
    action = modutil.get_tiered_moderation_action(message.author, self.config['actions'], meta.count)
    return action

def setup(bot : Bot):
  bot.register_plugin(ModLinks(bot))

def teardown(bot : Bot):
  bot.unregister_plugin("mod.links")