import io
import json
import os
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Union

from libtwitch import Bot, BotMessage, IrcChannel, ModerationAction, Plugin
from src import modutil

class EmoteSource(Enum):
  Twitch = auto()
  BttvGlobal = auto()
  BttvChannel = auto()
  FrankerFaceZGlobal = auto()
  FrankerFaceZChannel = auto()

@dataclass
class Emote:
  source: EmoteSource = None
  id: str = None
  text: str = None
  start: int = 0
  end: int = 0

class UtilEmote(Plugin):
  name = "util.emote"
  def __init__(self, bot):
    super().__init__(bot)
    self._bttv_global_emotes = {}
    self._frankerfacez_global_emotes = {}
    self.config = None

  def on_load(self):
    config_path = self.get_config_dir() + "/config.json"
    if not os.path.exists(config_path):
      self.config = {
        "use_bttv": True,
        "use_frankerfacez": True
      }
    else:
      with io.open(config_path) as f:
        jdata = json.load(f)
      if jdata is not None:
        self.config = jdata

    if self.config['use_bttv']:
      _, global_emotes = self.bot.request_handler.get_request_sync('https://api.betterttv.net/3/cached/emotes/global')
      if global_emotes is not None:
        jdata = json.loads(global_emotes)
        for jemote in jdata:
          self._bttv_global_emotes[jemote['code']] = jemote['id']

    if self.config['use_frankerfacez']:
      _, global_emotes = self.bot.request_handler.get_request_sync('https://api.frankerfacez.com/v1/set/global')
      if global_emotes is not None:
        jdata = json.loads(global_emotes)
        for set in jdata['sets']:
          for jemote in jdata['sets'][set]['emoticons']:
            self._frankerfacez_global_emotes[jemote['name']] = jemote['id']

  @staticmethod
  def _get_twitch_emotes(message: BotMessage) -> list[Emote]:
    emotes : list[Emote] = []
    if 'emotes' in message.tags and len(message.tags['emotes']) > 0:
      message_emote_types = message.tags['emotes'].split('/')
      for message_emote_type in message_emote_types:
        message_emote_type_parts = message_emote_type.split(':')
        emote_id = message_emote_type_parts[0]
        for message_emote_occurance in message_emote_type_parts[1].split(','):
          message_emote_position = message_emote_occurance.split('-')
          start = int(message_emote_position[0])
          end = int(message_emote_position[1])
          emote = Emote()
          emote.source = EmoteSource.Twitch
          emote.id = emote_id
          emote.text = message.text[start:end+1]
          emote.start = start
          emote.end = end
          emotes.append(emote)
    return emotes

  @staticmethod
  def _get_emotes(message: BotMessage, set: dict[str, int], source: EmoteSource) -> list[Emote]:
    emotes : list[Emote] = []
    words = message.text.split(' ')

    index = 0
    for word in words:
      if word in set:
        emote = Emote()
        emote.source = source
        emote.text = word
        emote.id = set[word]
        emote.start = index
        emote.end = index + len(word)
        emotes.append(emote)
      index += 1 + len(word)
    return emotes

  def list_bttv_channel_emotes(self, channel: Union[IrcChannel, int]) -> dict[str, int]:
    if isinstance(channel, IrcChannel):
      channel = channel.id

    _, channel_emotes = self.bot.request_handler.get_request_sync('https://api.betterttv.net/3/cached/users/twitch/%s' % channel)
    if channel_emotes is None:
      return {}

    bttv_channel_emotes = {}
    jdata = json.loads(channel_emotes)
    if 'channelEmotes' in jdata:
      for jemote in jdata['channelEmotes']:
        bttv_channel_emotes[jemote['code']] = jemote['id']
    if 'sharedEmotes' in jdata:
      for jemote in jdata['sharedEmotes']:
        bttv_channel_emotes[jemote['code']] = jemote['id']
    return bttv_channel_emotes

  def list_frankerfacez_channel_emotes(self, channel: Union[IrcChannel, int]) -> dict[str, int]:
    if isinstance(channel, IrcChannel):
      channel = channel.id

    _, channel_emotes = self.bot.request_handler.get_request_sync('https://api.frankerfacez.com/v1/room/id/%s' % channel)
    if channel_emotes is None:
      return {}

    jdata = json.loads(channel_emotes)
    if not 'sets' in jdata:
      return {}

    frankerfacez_channel_emotes = {}
    for set in jdata['sets']:
      for jemote in jdata['sets'][set]['emoticons']:
        frankerfacez_channel_emotes[jemote['name']] = jemote['id']
    return frankerfacez_channel_emotes

  def list_bttv_global_emotes(self) -> dict[str, int]:
    return self._bttv_global_emotes

  def list_frankerfacez_global_emotes(self) -> dict[str, int]:
    return self._frankerfacez_global_emotes

  def get_emotes(self, message: BotMessage) -> list[Emote]:
    emotes : list[Emote] = []
    emotes.extend(self._get_twitch_emotes(message))

    if self.config['use_bttv']:
      emotes.extend(self._get_emotes(message, self.list_bttv_global_emotes(), EmoteSource.BttvGlobal))
      emotes.extend(self._get_emotes(message, self.list_bttv_channel_emotes(message.channel), EmoteSource.BttvChannel))

    if self.config['use_frankerfacez']:
      emotes.extend(self._get_emotes(message, self.list_frankerfacez_global_emotes(), EmoteSource.FrankerFaceZGlobal))
      emotes.extend(self._get_emotes(message, self.list_frankerfacez_channel_emotes(message.channel), EmoteSource.FrankerFaceZChannel))

    return emotes

class ModEmote(Plugin):
  name = "mod.emote"
  def __init__(self, bot):
    super().__init__(bot)
    self.config = None

  def on_load(self):
    config_path = self.get_config_dir() + "/config.json"
    if not os.path.exists(config_path):
      self.config = {
        "min": 5,
        "max": 20,
        "percent": 0.60,
        "actions": [
          {
            "count": 1,
            "messages": [
              "@{user.name} -> Please refrain from spamming emotes."
            ],
            "mod_action": {
              "type": "timeout",
              "reason": "Spamming Emotes",
              "constant": 10
            }
          }
        ]
      }
    else:
      with io.open(config_path) as f:
        jdata = json.load(f)
      if jdata is not None:
        self.config = jdata

  def _on_moderate_impl(self, message : BotMessage) -> bool:
    util_plugin : Optional[UtilEmote] = self.bot.get_plugin("util.emote")
    if util_plugin is None:
      return False

    length = len(message.text)
    emotes = util_plugin.get_emotes(message)

    num_emotes = len(emotes)
    char_count = 0

    if num_emotes < self.config['min']:
      return False

    if num_emotes > self.config['max']:
      return True

    for emote in emotes:
      char_count += emote.end - emote.start

    if char_count / length > self.config["percent"]:
      return True

    return False

  def on_moderate(self, message : BotMessage) -> Optional[ModerationAction]:
    if not self._on_moderate_impl(message):
      return None

    meta = modutil.get_moderation_meta(self.bot, message.author, 'emotes')
    meta.invoke()
    meta.save(self.bot)
    action = modutil.get_tiered_moderation_action(message.author, self.config['actions'], meta.count)
    return action

def setup(bot : Bot):
  bot.register_plugin(UtilEmote(bot))
  bot.register_plugin(ModEmote(bot))

def teardown(bot : Bot):
  bot.unregister_plugin(UtilEmote.name)
  bot.unregister_plugin(ModEmote.name)