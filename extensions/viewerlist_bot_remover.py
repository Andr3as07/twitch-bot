import io
import json
import os

import requests

from libtwitch import Bot, ChatEvent, IrcChatter, BotMessage, Plugin

class ViewerlistBotRemover(Plugin):
  name = "mod.viewerlist_bot_remover"
  def __init__(self, bot):
    super().__init__(bot)
    self.bots : list[str] = []
    self.ignored = []

  def on_load(self):
    # Bot list
    url = "https://api.twitchinsights.net/v1/bots/all"
    print('Downloading bot list from "%s"...' % url)
    r = requests.get(url)
    for bot in json.loads(r.text)["bots"]:
      self.bots.append(bot[0])

    print("Loaded %s bots." % len(self.bots))

    # ignored users
    path = self.bot.get_config_dir() + "/ignored_users.txt"
    if os.path.exists(path):
      with io.open(path) as f:
        for username in f.readlines():
          username = username.strip()
          if len(username) == 0:
            continue
          self.ignored.append(username)

  def _ban(self, chatter : IrcChatter):
    # Don't ban yourself
    if chatter.name == self.bot.nickname:
      return

    # Don't ban an ignored user
    if chatter.name in self.ignored:
      return

    # Ban only known bots
    if not chatter.name in self.bots:
      return

    # Ban
    chatter.ban("Viewerlist bot")
    print("Banned %s!" % chatter.name)

  def on_chatter_join(self, join_event : ChatEvent):
    self._ban(join_event.chatter)

  def on_privmsg(self, message : BotMessage):
    self._ban(message.author)

def setup(bot : Bot):
  bot.register_plugin(ViewerlistBotRemover(bot))

def teardown(bot : Bot):
  bot.unregister_plugin("mod.viewerlist_bot_remover")