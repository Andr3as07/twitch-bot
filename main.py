from __future__ import annotations

import importlib
import sys
import logging
from datetime import time

from dotenv import load_dotenv

import libtwitch
from userdata import *
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

    # Botlist
    self.bots : list[str] = []
    url = "https://api.twitchinsights.net/v1/bots/all"
    self.logger.info('Downloading bot list from "%s"...' % url)
    r = requests.get(url)
    for bot in json.loads(r.text)["bots"]:
      self.bots.append(bot[0])
    self.logger.info("Loaded %s bots." % len(self.bots))
    self.logger.info("Ready")

    self._extensions = {}
    self._cogs : dict[str, libtwitch.Cog] = {}

  def add_cog(self, name : str, cog : libtwitch.Cog):
    self.logger.info("Adding cog \"%s\"..." % name)
    if not isinstance(cog, libtwitch.Cog):
      self.logger.warning("Failed to add cog \"%s\"! Cogs must derive from Cog!" % name)
      return False # cogs must derive from Cog

    self._cogs[name] = cog
    cog.invoke(libtwitch.CogEvent.SelfLoad)

    for other_cog_name in self._cogs: # Inform all other cogs
      if other_cog_name == name:
        continue
      self._cog_event(libtwitch.CogEvent.CogLoad, name) # Inform the cog of it's own loading

    self.logger.info("Added cog \"%s\"." % name)

  def get_cog(self, name : str):
    return self._cogs.get(name)

  def remove_cog(self, name : str):
    self.logger.info("Removing cog \"%s\"..." % name)
    cog = self._cogs.pop(name, None)
    if cog is None:
      self.logger.warning("Failed to remove cog \"%s\"! Cog is not loaded!" % name)
      return

    cog.invoke(libtwitch.CogEvent.SelfUnload) # Inform the cog of it's own unloading
    self._cog_event(libtwitch.CogEvent.CogUnload, name) # Inform all other cogs
    self.logger.info("Removed cog \"%s\"." % name)

  def _cog_event(self, event : libtwitch.CogEvent, *args, **kwargs):
    for cog in self._cogs:
      self._cogs[cog].invoke(event, *args, **kwargs)

  def load_extension(self, path):
    self.logger.info("Loading extension with path \"%s\"..." % path)

    try:
      name = importlib.util.resolve_name(path, None)
    except ImportError:
      self.logger.warning("Failed to load extension with path \"%s\"! Extension not found!" % path)
      return False # Extension not found

    if name in self._extensions:
      self.logger.warning("Failed to load extension \"%s\"! Extension already loaded!" % name)
      return False # Already loaded

    spec = importlib.util.find_spec(name)
    if spec is None:
      self.logger.warning("Failed to load extension \"%s\"! Extension not found!" % name)
      return False # Extension not found

    lib = importlib.util.module_from_spec(spec)
    sys.modules[name] = lib
    try:
      spec.loader.exec_module(lib)
    except Exception as ex:
      del sys.modules[name]
      self.logger.warning("Failed to load extension \"%s\"!" % name)
      return False # Failed to load extension

    try:
      setup = getattr(lib, 'setup')
    except AttributeError:
      del sys.modules[name]
      self.logger.warning("Failed to load extension \"%s\"! Entry point not found!" % name)
      return # Entry point not found

    try:
      setup(self)
    except Exception as ex:
      self.logger.warning("Failed to load extension \"%s\"! Error while calling extension entry point!" % name)
      del sys.modules[name]
      # self._remove_module_references(lib.__name__)
      self._call_extension_finalizer(lib, name)
      return False # Error while calling extension entry point
    else:
      self._extensions[name] = lib
      self.logger.info("Loaded extension \"%s\"." % name)

  def _call_extension_finalizer(self, lib, key):
    try:
      func = getattr(lib, 'teardown')
    except AttributeError:
      pass # We don't have a teardown function, that is ok
    else:
      try:
        func(self)
      except Exception:
        pass
    finally:
      self._extensions.pop(key, None)
      sys.modules.pop(key, None)
      name = lib.__name__
      for module in list(sys.modules.keys()):
        if name == module or module.startswith(name + "."):
          del sys.modules[module]

  def unload_extension(self, path):
    self.logger.info("Unloading extension with path \"%s\"..." % path)

    try:
      name = importlib.util.resolve_name(path, None)
    except ImportError:
      self.logger.warning("Failed to unload extension with path \"%s\"! Extension not found!" % path)
      return False # Extension not found

    lib = self._extensions.get(name)
    if lib is None:
      self.logger.warning("Failed to unload extension \"%s\"! Extension not loaded!" % name)
      return False # Extension not loaded

    self._call_extension_finalizer(lib, name)
    self.logger.info("Unloaded extension \"%s\"." % name)

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

  def get_tiered_moderation_action(self, msg : libtwitch.Message, actions : dict, count : int = 1) -> libtwitch.ModerationAction:
    moderation_action = libtwitch.ModerationAction(libtwitch.ModerationActionType.Nothing)
    best = None
    for action in actions:
      if best is None or count >= action["count"] > best["count"]:
        best = action
    if best is None:
      return moderation_action

    relative_count = count - best["count"]

    mod_action = best["mod_action"]
    mod_action_type = mod_action["type"]

    # Get appropriate moderation action
    if "reason" in mod_action:
      moderation_action.reason = mod_action["reason"]

    if mod_action_type == "nothing":
      moderation_action.action = libtwitch.ModerationActionType.Nothing
    elif mod_action_type == "remove_message":
      moderation_action.action = libtwitch.ModerationActionType.RemoveMessage
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

      moderation_action.action = libtwitch.ModerationActionType.Timeout
      moderation_action.duration = duration
    elif mod_action_type == "ban":
      moderation_action.action = libtwitch.ModerationActionType.Ban
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

  def mod_caps(self, msg : libtwitch.Message) -> bool:
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

  def mod_length(self, msg : libtwitch.Message) -> bool:
    config = self.config["length"]
    return len(msg.text) > config["max"]

  def mod_links(self, msg : libtwitch.Message) -> bool:
    # TODO: Allow specific domains and paths

    # findall() has been used with valid conditions for urls in string
    regex = r"((https?://)?(([^\s()<>]+)\.)*([a-z0-9\-.]+)\.([a-z]{2,})([^\s()<>?#]*)(?:\?([^\s()<>=#&]+=[^\s()<>=#&]*)(&([^\s()<>=#&]+=[^\s()<>=#&]*))*)?(?:#([^\s()<>]*))?)"
    urls = re.findall(regex, msg.text, re.IGNORECASE)

    return len(urls) > 0

  def mod_me(self, msg : libtwitch.Message) -> bool:
    return msg.text.startswith('ACTION ') and msg.text.endswith('')

  def moderation_helper(self, msg : libtwitch.Message, function, mod_tool_name : str, current_action : libtwitch.ModerationAction) -> libtwitch.ModerationAction:
    if function(msg):
      userdata = self.load_user(msg.author)
      view = userdata.view("moderation.%s" % mod_tool_name)
      view.set("count", view.get("count", 0) + 1)
      view.set("time", int(time.time()))

      self.save_user(userdata)
      action = self.get_tiered_moderation_action(msg, self.config[mod_tool_name]["actions"], view.get("count", 1))

      if action > current_action:
        return action
    return current_action

  def moderate(self, msg : libtwitch.Message) -> None:
    # Ignore Twitch Staff, Broadcasters and Moderators
    if msg.author.has_type(libtwitch.UserType.Broadcaster) or \
      msg.author.has_type(libtwitch.UserType.Twitch) or \
      msg.author.has_type(libtwitch.UserType.Moderator):
      return

    userdata = self.load_user(msg.author)

    # TODO: Find a way to only apply the most severe punishment and not multiple
    # TODO: Ignore specific users or groups

    action = libtwitch.ModerationAction(libtwitch.ModerationActionType.Nothing)

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

  def on_command(self, msg : libtwitch.Message, cmd : str, args : list[str]) -> None:
    self.logger.debug("on_command(%s, %s, %s)" % (msg.channel.name, cmd, args))

    for cog in self._cogs:
      if self._cogs[cog].on_command(msg, cmd, args):
        return

    self._cog_event(libtwitch.CogEvent.Command, msg, cmd, args)

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

    self._cog_event(libtwitch.CogEvent.Destruct)

    self.logger.info("Unloading all extensions...")
    for extension in self._extensions:
      self.unload_extension(extension)

    self.logger.info("Saving all user data...")
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

if __name__ == '__main__':
  load_dotenv()
  bot = MyBot("whyamitalking", os.getenv('CHAT_TOKEN'), "./config")
  bot.load_extension("cogs.Example")
  bot.connect()
  bot.unload_extension("cogs.Example")
  channel = bot.join_channel("Andr3as07")
  bot.run()
