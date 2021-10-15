import json
from dataclasses import dataclass
from enum import Enum, auto
from typing import Union

from libtwitch import Bot, BotMessage, IrcChannel, Plugin
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

  def on_load(self):
    _, global_emotes = self.bot.request_handler.get_request_sync('https://api.betterttv.net/3/cached/emotes/global')
    if global_emotes is not None:
      jdata = json.loads(global_emotes)
      for jemote in jdata:
        self._bttv_global_emotes[jemote['code']] = jemote['id']

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
    emotes.extend(self._get_emotes(message, self.list_bttv_global_emotes(), EmoteSource.BttvGlobal))
    emotes.extend(self._get_emotes(message, self.list_bttv_channel_emotes(message.channel), EmoteSource.BttvChannel))
    emotes.extend(self._get_emotes(message, self.list_frankerfacez_global_emotes(), EmoteSource.FrankerFaceZGlobal))
    emotes.extend(self._get_emotes(message, self.list_frankerfacez_channel_emotes(message.channel), EmoteSource.FrankerFaceZChannel))

    return emotes

def setup(bot : Bot):
  bot.register_plugin(UtilEmote(bot))

def teardown(bot : Bot):
  bot.unregister_plugin(UtilEmote.name)