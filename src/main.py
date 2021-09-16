from __future__ import annotations

import logging
import time
from typing import Any, Union

from dotenv import load_dotenv

import libtwitch
from src.userdata import Userdata, UserdataView
import requests
import random
import json
import os
import re
import io

def substitute_variables(text : str, data : dict[str, Any]) -> str:
  if not "{" in text:
    return text

  result = ""
  var = ""
  in_var = False
  for char in text:
    if char == "{":
      in_var = True
    elif char == "}":
      if var in data:
        result += str(data[var])
      else:
        result += "{" + var + "}"
      in_var = False
      var = ""
    else:
      if in_var:
        var += char
      else:
        result += char

  return result

class MyBot(libtwitch.Bot):
  def __init__(self, nickname : str, token : str, path : str):
    super().__init__(nickname, token)

    self.logger : logging.Logger = logging.getLogger('bot')
    c_handler = logging.StreamHandler()
    c_handler.setLevel(logging.DEBUG)
    c_formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s', '%Y-%m-%d %H:%M:%S')
    c_handler.setFormatter(c_formatter)
    self.logger.addHandler(c_handler)
    self.logger.setLevel(logging.DEBUG)

    self.logger.debug('Initialized with nick %s.' % nickname)

    self.config : dict = None
    self.load_config(path + "/config.json")
    if self.config is None:
      self.logger.critical("Bot can not run without valid config.")
      raise RuntimeError()
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
    self.config = config
    return True

  def load_user(self, chatter : libtwitch.Chatter) -> Userdata:
    if not chatter.id in self.user_data:
      path = "./data/users/%s.json" % chatter.id
      self.logger.debug('Loading userdata from "%s"' % path)
      try:
        with io.open(path, mode="r", encoding="utf-8") as f:
          raw = json.load(f)
          data = Userdata(raw)
      except: # TODO: FIX
        self.logger.debug('Failed to load userdata from "%s"! Generating default userdata.' % path)
        raw = {
          "id": chatter.id,
          "name": chatter.name,
          "display": chatter.display_name,
        }
        data = Userdata(raw)
      self.user_data[chatter.id] = data
    return self.user_data[chatter.id]

  def save_user(self, user : Union[Userdata, int]) -> None:
    if isinstance(user, int):
      if user in self.user_data:
        return
      user = self.user_data[user]

    while isinstance(user, UserdataView):
      user = user.data

    path = "./data/users/%s.json" % user.get("id")
    self.logger.debug('Saving userdata to "%s"' % path)
    try:
      with io.open(path, mode="w", encoding="utf-8") as f:
        user.set("stats.last_saved", int(time.time()))
        raw = user.raw
        json.dump(raw, f)
    except:  # TODO: FIX
      self.logger.warning('Failed to write userdata to "%s"' % path)

  def on_command(self, msg : libtwitch.Message, cmd : str, args : list[str]) -> None:
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

  def on_message(self, msg : libtwitch.Message):
    # Ignore self (echo)
    if msg.author.name.strip().lower() == self.nickname:
      self.logger.debug('Ignoring self (echo)')
      return

    # Ignored user list
    if msg.author.name.strip().lower() in self.ignored_users:
      self.logger.debug('Ignoring user "%s"' % msg.author.name)
      return

    # Continue command processing
    super().on_message(msg)

  def on_destruct(self):
    super().on_destruct()

    # Save all chatters
    for user in self.user_data:
      self.save_user(user)

  def on_connect(self):
    self.logger.debug("(Re)connected to twitch chat servers.")

  def on_channel_join(self, channel : libtwitch.Channel):
    self.logger.info("Joined channel %s" % channel.name)

  def on_channel_part(self, channel : libtwitch.Channel):
    self.logger.info("Parted from channel %s" % channel.name)

  def on_error(self, error : str):
    self.logger.error(error)
    pass

if __name__ == '__main__':
  load_dotenv()
  bot = MyBot(os.getenv('NICKNAME'), os.getenv('CHAT_TOKEN'), "config")
  bot.load_extension("8ball")
  bot.load_extension("viewerlist_bot_remover")
  bot.connect()
  channel = bot.join_channel(os.getenv('CHANNEL'))
  bot.start(libtwitch.RATE_MODERATOR)
