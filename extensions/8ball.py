import io
import os
import random

from libtwitch import Bot, BotMessage, Plugin

class Fun8Ball(Plugin):
  name = "fun.8ball"
  def __init__(self, bot):
    super().__init__(bot)
    self.responses = []
    self.emotes = []

  def on_load(self):
    responses_path = self.get_config_dir() + "/responses.txt"
    if os.path.exists(responses_path):
      with io.open(responses_path) as f:
        for response in f.readlines():
          response = response.strip()
          if len(response) == 0:
            continue
          self.responses.append(response)
      self.logger.info("Loaded %s responses." % len(self.responses))

    emotes_path = self.get_config_dir() + "/emotes.txt"
    if os.path.exists(emotes_path):
      with io.open(emotes_path) as f:
        for emote in f.readlines():
          emote = emote.strip()
          if len(emote) == 0:
            continue
          self.emotes.append(emote)
      self.logger.info("Loaded %s emotes." % len(self.emotes))

  def on_command(self, message : BotMessage, cmd : str, args : dict[str, str]):
    if cmd != "8ball":
      return

    line = random.choice(self.responses) + " " + random.choice(self.emotes)
    message.channel.chat(line)

def setup(bot : Bot):
  bot.register_plugin(Fun8Ball(bot))

def teardown(bot : Bot):
  bot.unregister_plugin("fun.8ball")