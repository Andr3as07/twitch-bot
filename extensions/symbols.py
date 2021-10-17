from typing import Optional

from libtwitch import Bot, BotMessage, ModerationAction, Plugin
from src import modutil, pluginutil, textutil

class ModSymbols(Plugin):
  name = "mod.symbols"
  def __init__(self, bot):
    super().__init__(bot)
    self.config = None

  def on_load(self):
    self.config = pluginutil.load_config(self, {
      "min": 5,
      "max": 50,
      "percent": 0.60,
      "actions": [
        {
          "count": 1,
          "messages": [
            "@{user.name} -> Please refrain from spamming symbols."
          ],
          "mod_action": {
            "type": "nothing",
            "reason": "Using symbols",
            "constant": 10
          }
        }
      ]
    })

  def on_moderate(self, message : BotMessage) -> Optional[ModerationAction]:
    contains, symol_range = textutil.contains_symbols(message.text)
    if not contains:
      return None

    meta = modutil.get_moderation_meta(self.bot, message.author, 'symbols')
    meta.invoke()
    meta.save(self.bot)
    action = modutil.get_tiered_moderation_action(message.author, self.config['actions'], meta.count)
    return action

def setup(bot : Bot):
  bot.register_plugin(ModSymbols(bot))

def teardown(bot : Bot):
  bot.unregister_plugin("mod.symbols")