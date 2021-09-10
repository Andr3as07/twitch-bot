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

def perform_mod_punishment(msg, mod_action, count = 0):
  type = mod_action["type"]
  if type == "nothing":
    return 0
  elif type == "remove_message":
    msg.delete()
    return 0
  elif type == "timeout":
    base = 600
    if "base" in mod_action:
      base = mod_action["base"]
    additional = 3600
    if "additional" in mod_action:
      additional = mod_action["additional"]
    duration = base + (count * additional)

    reason = None
    if "reason" in mod_action:
      reason = mod_action["reason"]

    msg.author.timeout(duration, reason)
    return duration
  elif type == "ban":
    reason = None
    if "reason" in mod_action:
      reason = mod_action["reason"]

    msg.author.ban(reason)
    return 0
  else:
    print("Unknown mod action: %s" % type)
    return 0

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

def perform_tiered_action(msg, actions, count = 1):
  best = None
  for action in actions:
    if best is None or count >= action["count"] > best["count"]:
      best = action
  if best is None:
    return

  tiered_action_count = count - best["count"]

  duration = perform_mod_punishment(msg, best["mod_action"], tiered_action_count)

  if len(best["messages"]) > 0:
    text = random.choice(best["messages"])
    data = {
      "user.name": msg.author.name,
      "count": count,
      "duration": duration
    }
    msg.channel.chat(substitute_variables(text, data))

class MyBot(twitch.Bot):
  def __init__(self, nickname, token, path):
    super().__init__(nickname, token)
    self.config = None
    self.load_config(path)
    self.user_data = {} # TODO: FIX: This should be separated into the different channels
    self.bots = []

  def load_config(self, path):
    try:
      with io.open(path, mode="r", encoding="utf-8") as f:
        config = json.load(f)
    except: # TODO: FIX
      print("Failed to load config")
      return

    self.config = config

  def load_user(self, chatter):
    if not chatter.id in self.user_data:
      path = "./data/users/%s.json" % chatter.id
      try:
        with io.open(path, mode="r", encoding="utf-8") as f:
          raw = json.load(f)
          data = Userdata(raw)
      except:  # TODO: FIX
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
    try:
      with io.open(path, mode="w", encoding="utf-8") as f:
        user.set("stats.last_saved", int(time.time()))
        raw = user.raw
        json.dump(raw, f)
    except:  # TODO: FIX
      print("Failed to write user data for %s" % user.get("name"))

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
    urls = re.findall(regex, msg.text)

    return len(urls) > 0

  def moderate(self, msg, userdata):
    # Ignore Twitch Staff, Broadcasters and Moderators
    if msg.author.has_type(twitch.UserType.Broadcaster) or \
      msg.author.has_type(twitch.UserType.Twitch) or \
      msg.author.has_type(twitch.UserType.Moderator):
      return

    # TODO: Ignore specific users

    # Caps "THIS IS A SHOUTED MESSAGE"
    if self.mod_caps(msg):
      view = userdata.view("moderation.caps")
      view.set("count", view.get("count", 0) + 1)
      view.set("time", int(time.time()))

      self.save_user(userdata)
      perform_tiered_action(msg, self.config["caps"]["actions"], view.get("count", 1))

    # Length "<paragraph of text>"
    if self.mod_length(msg):
      view = userdata.view("moderation.length")
      view.set("count", view.get("count", 0) + 1)
      view.set("time", int(time.time()))

      self.save_user(userdata)
      perform_tiered_action(msg, self.config["length"]["actions"], view.get("count", 1))

    # TODO: Words "<swear>"

    # Links "example.com"
    if self.mod_links(msg):
      view = userdata.view("moderation.links")
      view.set("count", view.get("count", 0) + 1)
      view.set("time", int(time.time()))

      self.save_user(userdata)
      perform_tiered_action(msg, self.config["links"]["actions"], view.get("count", 1))

    # TODO: Repeats "Hi Hi Hi Hi Hi"
    # TODO: Long words "Pneumonoultramicroscopicsilicovolcanoconiosis"
    # TODO: Single character words "S p a m"
    # TODO: Symbols "▐Z̵̬͝a̷̟͋l̴̯̪͊̕g̵̳̉ö̸̖́ ⓔⓧⓐⓜⓟⓛⓔ"
    # TODO: Emotes "Kappa Kappa Kappa Kappa Kappa Kappa Kappa Kappa"
    # TODO: Numbers "1235123541254154123123"
    # TODO: Repeated messages
    # TODO: /me
    # TODO: Command spam "!bla"
    # TODO: Fake messages "message deleted by a moderator"

  def on_command(self, msg, cmd, args, userdata):
    print("%s %s" % (cmd, args))

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
    print("[%s] %s: %s" % (msg.channel.name, msg.author.display_name, msg.text))
    userdata = self.load_user(msg.author)
    self.moderate(msg, userdata)

    if not msg.text.startswith('?'):
      return

    args = msg.text.strip().split(' ')
    if len(args) == 0:
      return

    if len(args[0]) == 1:
      return

    cmd = args[0][1:]
    args.pop(0)

    self.on_command(msg, cmd, args, userdata)

  def on_destruct(self):
    for user in self.user_data:
      self.save_user(user)

  def on_ready(self):
    print("Downloading bot list...")
    url = "https://api.twitchinsights.net/v1/bots/all"
    r = requests.get(url)
    self.bots = []
    for bot in json.loads(r.text)["bots"]:
      self.bots.append(bot[0])
    print("Loaded %s bots." % len(self.bots))
    print("Ready")

  def on_connect(self):
    print("(Re)connected to twitch chat servers.")

  def on_channel_join(self, channel):
    print("Joined channel %s" % channel.name)

  def on_channel_part(self, channel):
    print("Parted from channel %s" % channel.name)

  def on_error(self, error):
    print("ERROR: " + error)

if __name__ == '__main__':
  load_dotenv()
  bot = MyBot("whyamitalking", os.getenv('CHAT_TOKEN'), "./config/config.json")
  bot.connect()
  channel = bot.join_channel("Andr3as07")
  bot.run()
