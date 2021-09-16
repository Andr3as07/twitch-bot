import os
from enum import Enum, auto
from typing import Union

from libtwitch.bot import BotMessage
from libtwitch.moderation_action import ModerationAction
from libtwitch.core import IrcChannel, IrcChatter, IrcMessage

class PluginEvent(Enum):
  # Bot events
  Destruct = auto()

  # IRC events
  RawIngress = auto()
  RawEgress = auto() # This is considered dangerous
  Connect = auto()
  Disconnect = auto()
  Error = auto() # TODO
  ErrorBaned = auto() # TODO
  ErrorTimedOut = auto() # TODO
  Unknown = auto()
  ChannelJoin = auto()
  ChannelPart = auto()
  ChatterJoin = auto()
  ChatterPart = auto()
  Moderate = auto()
  Privmsg = auto()
  Message = auto()
  Command = auto()
  Whisper = auto() # TODO

  # Community events
  Bits = auto()
  Raid = auto()
  Subscribe = auto()

  # Plugin events
  SelfLoad = auto()
  SelfUnload = auto()
  PluginLoad = auto()
  PluginUnload = auto()

DEFAULT_PLUGIN_NAME = 'UNNAMED PLUGIN'

class Plugin:
  name = DEFAULT_PLUGIN_NAME

  @classmethod
  def get_name(cls):
    if cls.name == DEFAULT_PLUGIN_NAME:
      return cls.__NAME__
    return cls.name

  def __init__(self, bot):
    self.bot = bot

  def on_event(self, plugin_event : PluginEvent, *args, **kwargs) -> Union[None, ModerationAction]:
    # Bot events
    if plugin_event == PluginEvent.Destruct:
      self.on_destruct()

    # IRC events
    elif plugin_event == PluginEvent.RawIngress:
      self.on_raw_ingress(args[0])
    elif plugin_event == PluginEvent.RawEgress:
      self.on_raw_egress(args[0])
    elif plugin_event == PluginEvent.Connect:
      self.on_connect()
    elif plugin_event == PluginEvent.Disconnect:
      self.on_disconnect()
    elif plugin_event == PluginEvent.Unknown:
      self.on_unknown(args[0])
    elif plugin_event == PluginEvent.ChannelJoin:
      self.on_channel_join(args[0])
    elif plugin_event == PluginEvent.ChannelPart:
      self.on_channel_part(args[0])
    elif plugin_event == PluginEvent.ChatterJoin:
      self.on_chatter_join(args[0])
    elif plugin_event == PluginEvent.ChatterPart:
      self.on_chatter_part(args[0])
    elif plugin_event == PluginEvent.Moderate:
      return self.on_moderate(args[0])
    elif plugin_event == PluginEvent.Privmsg:
      self.on_privmsg(args[0])
    elif plugin_event == PluginEvent.Message:
      self.on_message(args[0])
    elif plugin_event == PluginEvent.Command:
      self.on_command(args[0], args[1], args[2])

    # Plugin events
    elif plugin_event == PluginEvent.SelfLoad:
      self.on_load()
    elif plugin_event == PluginEvent.SelfUnload:
      self.on_unload()
    elif plugin_event == PluginEvent.PluginLoad:
      self.on_plugin_load(args[0])
    elif plugin_event == PluginEvent.PluginUnload:
      self.on_unload(args[0])
    else:
      print("ERROR: Unhandled event %s" % plugin_event)

  # Bot events
  def on_destruct(self):
    """
    called when the underling bot is about to destruct
    """

  # IRC events
  def on_raw_ingress(self, data : str):
    """
    called when the irc connection receives new data
    :param data: the raw data formatted as a utf-8 string
    """

  def on_raw_egress(self, data : str):
    """
    called when the irc connection sends data
    :param data: the raw data formatted as a utf-8 string
    """

  def on_connect(self):
    """
    called when the underling connection to the twitch irc servers in established
    """

  def on_disconnect(self):
    """
    called when the underling connection to the twitch irc servers in lost
    """

  def on_unknown(self, data):
    """
    called when a unexpected line occurs in the irc chat. (see on_raw_ingress)
    :param data: the raw data formatted as a utf-8 string
    """

  def on_channel_join(self, channel : IrcChannel):
    """
    triggered when the bot connects to a channel
    :param channel: the joined channel
    """

  def on_channel_part(self, channel : IrcChannel):
    """
    triggered when the bot leaves to a channel
    :param channel: the parted channel
    """

  def on_chatter_join(self, chatter : IrcChatter):
    """
    triggered when a chatter joins to a channel
    :param chatter: the chatter
    """

  def on_chatter_part(self, chatter : IrcChatter):
    """
    triggered when a chatter parts to a channel
    :param chatter: the chatter
    """

  def on_moderate(self, message : BotMessage) -> ModerationAction:
    """
    called when a privmsg is received in a channel
    note: this includes all messages sent to the chat
    note: this is called before on_privmsg
    :param message: the received message
    :return: the moderation action to take or None
    """

  def on_privmsg(self, message : BotMessage):
    """
    called when a privmsg is received in a channel
    note: this includes all messages sent to the chat
    :param message: the received message
    """

  def on_message(self, message : BotMessage):
    """
    called when a message is received in a channel
    note: this does not include commands (see on_privmsg and on_command)
    :param message: the received message
    """

  def on_command(self, message : BotMessage, cmd : str, args : dict[str, str]):
    """
    called when a command is recognized in a channel
    :param message: the received message
    :param cmd: the recognized command name
    :param args: the parsed arguments of the command
    """

  # Plugin events
  def on_load(self):
    """
    called when the plugin is loaded
    """

  def on_unload(self):
    """
    called when the plugin is unloaded
    """

  def on_plugin_load(self, plugin_name : str):
    """
    called when another plugin has been loaded
    :param plugin_name: the name of the other plugin
    """

  def on_unload(self, plugin_name : str):
    """
    called when another plugin is being unloaded
    :param plugin_name: the name of the other plugin
    """

  @staticmethod
  def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

  def get_config_dir(self):
    path = self.bot.get_config_dir() + "/" + self.get_name().replace('.', '/')
    self._ensure_dir(path)
    return path

  def get_data_dir(self):
    path = self.bot.get_data_dir() + "/" + self.get_name().replace('.', '/')
    self._ensure_dir(path)
    return path