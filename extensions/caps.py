from typing import Optional

from extensions.emote import Emote, UtilEmote
from libtwitch import Bot, BotMessage, ModerationAction, Plugin
from src import modutil, pluginutil

class ModCaps(Plugin):
  name = "mod.caps"
  def __init__(self, bot):
    super().__init__(bot)
    self.config = None

  def on_load(self):
    self.config = pluginutil.load_config(self, {
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
    })

  @staticmethod
  def _remove_emotes(text: str, emotes: list[Emote]) -> str:
    res = ''
    for index in range(0, len(text)):
      in_emote = False
      for emote in emotes:
        if emote.start <= index <= emote.end:
          in_emote = True
          break
      if in_emote:
        continue
      res += text[index]
    return res

  def _on_moderate_impl(self, message : BotMessage) -> bool:
    text = message.text
    util_emote_plugin : Optional[UtilEmote] = self.bot.get_plugin("util.emote")
    if util_emote_plugin is not None:
      emotes = util_emote_plugin.get_emotes(message)
      text = self._remove_emotes(text, emotes)

    num_caps = 0
    length = len(text)
    for char in text:
      if 'A' <= char <= 'Z':
        num_caps += 1

    if num_caps < self.config['min']:
      return False

    if num_caps > self.config['max']:
      return True

    if num_caps / length > self.config["percent"]:
      return True

    return False

  def on_moderate(self, message : BotMessage) -> Optional[ModerationAction]:
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