import logging
from enum import IntEnum
from functools import total_ordering

from dotenv import load_dotenv
import time
import bot as twitch
from userdata import *
import requests
import random
import json
import os
import re
import io

class ModerationActionType(IntEnum):
  Nothing = 0
  RemoveMessage = 1
  Timeout = 2
  Ban = 3

@total_ordering
class ModerationAction:
  def __init__(self, action, duration = 0, reason = None, response = None):
    self.action = action
    self.reason = reason
    self.response = response
    self.duration = duration

  def invoke(self, message):
    # Respond if we have a response
    if self.response is not None:
      #if message is not None:
      #  message.respond(self.response)
      #else:
      message.channel.chat(self.response)

    # Perform the actual moderation action
    if self.action == ModerationActionType.Nothing:
      return True # Do nothing
    elif self.action == ModerationActionType.RemoveMessage:
      if message is None: # We can't remove the message if we don't know what message we are talking about.
        return False
      message.delete()
    elif self.action == ModerationActionType.Timeout:
      message.author.timeout(self.duration, self.reason)
      return True
    elif self.action == ModerationActionType.Ban:
      message.author.ban(self.reason)
      return True

    return False

  def __eq__(self, other):
    if self.action == other.action:
      if self.action == ModerationActionType.Timeout:
        return self.duration == other.duration
      return True
    return False

  def __ne__(self, other):
    return not (self == other)

  def __lt__(self, other):
    if self.action < other.action:
      return True

    if self.action == other.action and self.action == ModerationActionType.Timeout:
      if self.duration < other.duration:
        return True

    if self.reason is None and other.reason is not None:
      return True

    if self.response is None and other.response is not None:
      return True

    return False

def substitute_variables(text, data):
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

class MyBot(twitch.Bot):
  def __init__(self, nickname, token, path):
    super().__init__(nickname, token)
    self.logger = logging.getLogger('bot')
    c_handler = logging.StreamHandler()
    c_handler.setLevel(logging.DEBUG)
    c_formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s', '%Y-%m-%d %H:%M:%S')
    c_handler.setFormatter(c_formatter)
    self.logger.addHandler(c_handler)
    self.logger.setLevel(logging.DEBUG)

    self.logger.debug('Initialized with nick %s.' % nickname)

    self.config = None
    self.load_config(path + "/config.json")
    if self.config is None:
      self.logger.critical("Bot can not run without valid config.")
      raise RuntimeError()
    self.user_data = {} # TODO: FIX: This should be separated into the different channels

    # Ignored users
    self.ignored_users = []
    if os.path.exists(path + "/ignored_users.txt"):
      self.logger.info("Loading ignored users list...")
      try:
        with io.open(path + "/ignored_users.txt") as f:
          for username in f.readlines():
            self.ignored_users.append(username.strip().lower())
        self.logger.info("Ignoring %s usernames." % len(self.ignored_users))
      except:
        self.logger.error("Failed to load ignored users list!")

    # Botlist
    self.bots = []
    url = "https://api.twitchinsights.net/v1/bots/all"
    self.logger.info('Downloading bot list from "%s"...' % url)
    r = requests.get(url)
    for bot in json.loads(r.text)["bots"]:
      self.bots.append(bot[0])
    self.logger.info("Loaded %s bots." % len(self.bots))
    self.logger.info("Ready")

  def load_config(self, path):
    self.logger.info('Loading config from "%s"' % path)
    try:
      with io.open(path, mode="r", encoding="utf-8") as f:
        config = json.load(f)
    except: # TODO: FIX
      self.logger.error("Failed to load config!")
      return False

    self.logger.debug("Successfully loaded config.")
    self.config = config

  def load_user(self, chatter):
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

  def save_user(self, user):
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


  def get_tiered_moderation_action(self, msg, actions, count=1):
    best = None
    for action in actions:
      if best is None or count >= action["count"] > best["count"]:
        best = action
    if best is None:
      return


    relative_count = count - best["count"]

    mod_action = best["mod_action"]
    mod_action_type = mod_action["type"]

    # Get appropriate moderation action
    moderation_action = ModerationAction(ModerationActionType.Nothing)
    if "reason" in mod_action:
      moderation_action.reason = mod_action["reason"]

    if mod_action_type == "nothing":
      moderation_action.action = ModerationActionType.Nothing
    elif mod_action_type == "remove_message":
      moderation_action.action = ModerationActionType.RemoveMessage
    elif mod_action_type == "timeout":
      # Calculate timeout duration
      # t = a*x^2 + b*x + c
      constant = 600
      if "constant" in mod_action:
        constant = mod_action["constant"]
      linear = 0
      if "linear" in mod_action:
        linear = mod_action["linear"]
      quadratic = 0
      if "quadratic" in mod_action:
        quadratic = mod_action["quadratic"]
      duration = (quadratic * relative_count * relative_count) + (linear * relative_count) + constant

      moderation_action.action = ModerationActionType.Timeout
      moderation_action.duration = duration
    elif mod_action_type == "ban":
      moderation_action.action = ModerationActionType.Ban
    else:
      self.logger.warning("Unknown mod action: %s" % mod_action_type)

    if len(best["messages"]) > 0:
      text = random.choice(best["messages"])
      data = {
        "user.name": msg.author.name,
        "count": count,
        "duration": moderation_action.duration
      }
      moderation_action.response = substitute_variables(text, data)

    return moderation_action

  def mod_caps(self, msg):
    config = self.config["caps"]

    num_caps = 0
    length = len(msg.text)
    for char in msg.text:
      if 'A' <= char <= 'Z':
        num_caps += 1

    if num_caps < config['min']:
      return False

    if num_caps > config['max']:
      return True

    if num_caps / length > config["percent"]:
      return True

    return False

  def mod_length(self, msg):
    config = self.config["length"]
    return len(msg.text) > config["max"]

  def mod_links(self, msg):
    # TODO: Allow specific domains and paths

    # findall() has been used with valid conditions for urls in string
    regex = r"((https?://)?(([^\s()<>]+)\.)*([a-z0-9\-.]+)\.([a-z]{2,})([^\s()<>?#]*)(?:\?([^\s()<>=#&]+=[^\s()<>=#&]*)(&([^\s()<>=#&]+=[^\s()<>=#&]*))*)?(?:#([^\s()<>]*))?)"
    urls = re.findall(regex, msg.text, re.IGNORECASE)

    return len(urls) > 0

  def mod_me(self, msg):
    return msg.text.startswith('ACTION ') and msg.text.endswith('')

  def moderation_helper(self, msg, function, mod_tool_name, most_appropriate_mod_action):
    if function(msg):
      userdata = self.load_user(msg.author)
      view = userdata.view("moderation.%s" % mod_tool_name)
      view.set("count", view.get("count", 0) + 1)
      view.set("time", int(time.time()))

      self.save_user(userdata)
      action = self.get_tiered_moderation_action(msg, self.config[mod_tool_name]["actions"], view.get("count", 1))

      if action > most_appropriate_mod_action:
        return action
    return most_appropriate_mod_action

  def moderate(self, msg):
    # Ignore Twitch Staff, Broadcasters and Moderators
    if msg.author.has_type(twitch.UserType.Broadcaster) or \
      msg.author.has_type(twitch.UserType.Twitch) or \
      msg.author.has_type(twitch.UserType.Moderator):
      return

    userdata = self.load_user(msg.author)

    # TODO: Find a way to only apply the most severe punishment and not multiple
    # TODO: Ignore specific users or groups

    action = ModerationAction(ModerationActionType.Nothing)

    # Caps "THIS IS A SHOUTED MESSAGE"
    action = self.moderation_helper(msg, self.mod_caps, "caps", action)

    # Length "<paragraph of text>"
    action = self.moderation_helper(msg, self.mod_length, "length", action)

    # TODO: Words "<swear>"

    # Links "example.com"
    action = self.moderation_helper(msg, self.mod_links, "links", action)

    # TODO: Repeats "Hi Hi Hi Hi Hi"
    # TODO: Long words "Pneumonoultramicroscopicsilicovolcanoconiosis"
    # TODO: Single character words "S p a m"
    # TODO: Symbols "▐Z̵̬͝a̷̟͋l̴̯̪͊̕g̵̳̉ö̸̖́ ⓔⓧⓐⓜⓟⓛⓔ"
    # TODO: Emotes "Kappa Kappa Kappa Kappa Kappa Kappa Kappa Kappa"
    # TODO: Numbers "1235123541254154123123"
    # TODO: Repeated messages
    # /me
    action = self.moderation_helper(msg, self.mod_me, "me", action)

    # TODO: Command spam "!bla"
    # TODO: Fake messages "message deleted by a moderator"

    action.invoke(msg)

  def on_command(self, msg, cmd, args, userdata):
    self.logger.debug("on_command(%s, %s, %s)" % (msg.channel.name, cmd, args))

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

  def on_message(self, msg):
    self.logger.debug('on_message(%s, %s, "%s")' % (msg.channel.name, msg.author.display_name, msg.text))

    # Ignore self (echo)
    if msg.author.name.strip().lower() == self.nickname:
      self.logger.debug('Ignoring self (echo)')
      return

    # Ignored user list
    if msg.author.name.strip().lower() in self.ignored_users:
      self.logger.debug('Ignoring user "%s"' % msg.author.name)
      return

    self.moderate(msg)

    # Commands must start with this prefix
    if not msg.text.startswith('?'):
      return

    # Commands must contain at least the command name
    args = msg.text.strip().split(' ')
    if len(args) == 0:
      return
    elif len(args[0]) == 1:
      return

    # The command name is up to the first space.
    # Anything after that is a space separated list of arguments
    cmd = args[0][1:]
    args.pop(0)

    self.on_command(msg, cmd, args)

  def on_destruct(self):
    self.logger.debug("on_destruct")
    self.logger.info("Saving all user data...")
    for user in self.user_data:
      self.save_user(user)

  def on_connect(self):
    self.logger.debug("(Re)connected to twitch chat servers.")

  def on_channel_join(self, channel):
    self.logger.info("Joined channel %s" % channel.name)

  def on_channel_part(self, channel):
    self.logger.info("Parted from channel %s" % channel.name)

  def on_error(self, error):
    self.logger.error(error)

if __name__ == '__main__':
  load_dotenv()
  bot = MyBot("whyamitalking", os.getenv('CHAT_TOKEN'), "./config")
  bot.connect()
  channel = bot.join_channel("Andr3as07")
  bot.run()
