from typing import Optional

from libtwitch import Bot, BotMessage, ModerationAction, Plugin
from src import modutil, pluginutil

class ModLength(Plugin):
  name = "mod.length"
  def __init__(self, bot):
    super().__init__(bot)
    self.config = None

  def on_load(self):
    self.config = pluginutil.load_config(self, {
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
    })

  def _on_moderate_impl(self, message : BotMessage) -> bool:
    length = self.config["length"]
    return len(message.text) > length

  def on_moderate(self, message : BotMessage) -> Optional[ModerationAction]:
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