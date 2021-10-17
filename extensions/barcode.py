import re
from typing import Optional

from libtwitch import Bot, BotMessage, ModerationAction, Plugin
from src import modutil, pluginutil

class ModBarcode(Plugin):
  name = "mod.barcode"
  def __init__(self, bot):
    super().__init__(bot)
    self.config = None

  def on_load(self):
    self.config = pluginutil.load_config(self, {
      "min_username": 3,
      "min_message": 5,
      "actions": [
        {
          "count": 1,
          "messages": [
            "@{user.name} -> Stop using barcodes."
          ],
          "mod_action": {
            "type": "timeout",
            "reason": "Using barcodes",
            "constant": 10
          }
        }
      ]
    })

  @staticmethod
  def _detect_barcode(text: str, length: int):
    regex = r"[Il]{%s,}" % length
    matches = re.findall(regex, text)
    return len(matches) > 0

  def _on_moderate_impl(self, message : BotMessage) -> bool:
    if self._detect_barcode(message.text, self.config['min_message']):
      return True

    if self._detect_barcode(message.author.display_name, self.config['min_username']):
      return True

    if self._detect_barcode(message.author.login, self.config['min_username']):
      return True

    return False

  def on_moderate(self, message : BotMessage) -> Optional[ModerationAction]:
    if not self._on_moderate_impl(message):
      return None

    meta = modutil.get_moderation_meta(self.bot, message.author, 'barcode')
    meta.invoke()
    meta.save(self.bot)
    action = modutil.get_tiered_moderation_action(message.author, self.config['actions'], meta.count)
    return action

def setup(bot : Bot):
  bot.register_plugin(ModBarcode(bot))

def teardown(bot : Bot):
  bot.unregister_plugin(ModBarcode.name)