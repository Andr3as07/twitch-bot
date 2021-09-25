from __future__ import annotations

import logging

from redis import Redis
from dotenv import load_dotenv

import libtwitch
import json
import os
import io

from libtwitch import Datastore, FileDatastore

class MyBot(libtwitch.Bot):
  def __init__(self, nickname : str, token : str, path : str, datastore : Datastore):
    super().__init__(nickname, token, datastore, '?')

    self.logger : logging.Logger = logging.getLogger('bot')
    c_handler = logging.StreamHandler()
    c_handler.setLevel(logging.DEBUG)
    c_formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s', '%Y-%m-%d %H:%M:%S')
    c_handler.setFormatter(c_formatter)
    self.logger.addHandler(c_handler)
    self.logger.setLevel(logging.DEBUG)

    self.logger.debug('Initialized with nick %s.' % nickname)

    self.user_data : dict = {} # TODO: FIX: This should be separated into the different channels

    # Ignored users
    self.ignored_users : list[str] = []
    if os.path.exists(path + "/ignored_users.txt"):
      self.logger.info("Loading ignored users list...")
      try:
        with io.open(path + "/ignored_users.txt") as f:
          for username in f.readlines():
            self.ignored_users.append(username.strip().lower())
        self.logger.info("Ignoring %s usernames." % len(self.ignored_users))
      except:
        self.logger.error("Failed to load ignored users list!")

  def load_config(self, path : str) -> bool:
    self.logger.info('Loading config from "%s"' % path)
    try:
      with io.open(path, mode="r", encoding="utf-8") as f:
        config = json.load(f)
    except: # TODO: FIX
      self.logger.error("Failed to load config!")
      return False

    self.logger.debug("Successfully loaded config.")
    return True

  def on_command(self, msg : libtwitch.BotMessage, cmd : str, args : list[str]) -> None:
    self.logger.debug("on_command(%s, %s, %s)" % (msg.channel.name, cmd, args))

    super().on_command(msg, cmd, args)

    # Utility
    # TODO: Help (!help, !commands)
    # TODO: Shoutout
    # TODO: Stats (watchtime, followage, lastseen, lastactive)
    # TODO: Change scene
    # TODO: Game
    # TODO: Ads
    # TODO: Title

    # Moderation
    # TODO: Nuke (Remove specific phrases from chat)

    # Games
    # TODO: Bingo
    # TODO: Raffle # TODO: Maybe move to message
    # TODO: Emote pyramid # TODO: Maybe move to message
    # TODO: Emote combo # TODO: Maybe move to message
    # TODO: Duel
    # TODO: Love
    # TODO: 8Ball
    # TODO: Slots
    # TODO: Roulette
    # TODO: Seppuku

    # Media
    # TODO: Songrequest
    # TODO: Song queue

    # Community
    # TODO: Giveaway
    # TODO: Poll
    # TODO: Quotes

    # TODO: Custom commands

  def on_message(self, msg : libtwitch.BotMessage):
    # Ignore self (echo)
    if msg.author.login.strip().lower() == self.nickname:
      self.logger.debug('Ignoring self (echo)')
      return

    # Ignored user list
    if msg.author.login.strip().lower() in self.ignored_users:
      self.logger.debug('Ignoring user "%s"' % msg.author.login)
      return

    # Continue command processing
    super().on_message(msg)

  def on_raw_ingress(self, data : str):
    print("> " + data)

  def on_raw_egress(self, data : str):
    print("< " + data)

  def on_connect(self):
    self.logger.debug("(Re)connected to twitch chat servers.")

  def on_channel_join(self, channel : libtwitch.IrcChannel):
    self.logger.info("Joined channel %s" % channel.name)

  def on_channel_part(self, channel : libtwitch.IrcChannel):
    self.logger.info("Parted from channel %s" % channel.name)

  def on_error(self, error : str):
    self.logger.error(error)
    pass

if __name__ == '__main__':
  load_dotenv()

  r = None
  if os.getenv('USE_REDIS') == 'True':
    r = Redis(host=os.getenv('REDIS_HOST'), port=int(os.getenv('REDIS_PORT')))

  datastore = FileDatastore("./data", r)
  bot = MyBot(
    os.getenv('NICKNAME'),
    os.getenv('CHAT_TOKEN'),
    "./config",
    datastore)
  # Commands
  bot.load_extension("8ball")

  # Moderation
  bot.load_extension("viewerlist_bot_remover")
  bot.load_extension("caps")
  bot.load_extension("length")
  bot.load_extension("links")
  bot.load_extension("me")

  bot.connect()
  channel = bot.join_channel(os.getenv('CHANNEL'))
  bot.start(libtwitch.RATE_MODERATOR)
