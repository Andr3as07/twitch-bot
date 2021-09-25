from __future__ import annotations

import libtwitch
import threading
from queue import Queue

from typing import Optional, Union
from time import sleep
import socket
import re

HOST = "irc.twitch.tv"
PORT = 6667
RATE_USER = 20 / 30  # messages per second
RATE_MODERATOR = 100 / 30  # messages per second

RE_TAG_PART = r"(?:@([^\s=;]+=[^\s;]*(?:;(?:[^\s=;]+=[^\s;]*))*))?\s?"
RE_CHAT_MSG = r"^%s:([^\s!]+)!(?:[^\s@]+)@(?:[^\s\.]+)(?:\.tmi\.twitch\.tv PRIVMSG) #([^\s!]+) :(.+)$" % RE_TAG_PART
RE_USERNOTICE = r"^%s:(?:tmi\.twitch\.tv USERNOTICE) #([^\s!]+)(?: :(.+))?$" % RE_TAG_PART
RE_ROOMSTATE = r"^%s:(?:tmi\.twitch\.tv ROOMSTATE) #([^\s!]+)$" % RE_TAG_PART
RE_JOIN = r"^:([^\s!]+)!(?:[^\s@]+)@(?:[^\s\.]+)(?:\.tmi\.twitch\.tv JOIN) #([^\s!]+)$"
RE_PART = r"^:([^\s!]+)!(?:[^\s@]+)@(?:[^\s\.]+)(?:\.tmi\.twitch\.tv PART) #([^\s!]+)$"

class IrcConnection:
  def __init__(self, nickname, token):
    self.nickname = nickname.lower()
    self._token : str = token
    self._socket : Optional[socket] = None
    self._channels : dict[str, libtwitch.IrcChannel] = {}
    self._back_buffer : list[str] = []

    self.rate : float = RATE_USER
    self._running : bool = False

    self._ingress_thread : Optional[threading.Thread] = None
    self._egress_thread : Optional[threading.Thread] = None

    self._egress_queue : Queue = Queue()
    self._egress_queue_lock : threading.Lock = threading.Lock()

    self.on_ready()

  def connect(self):
    global HOST
    global PORT
    self._socket = socket.socket()
    self._socket.connect((HOST, PORT))
    self.send("PASS %s" % self._token)
    self.send("NICK %s" % self.nickname)
    self.send("CAP REQ :twitch.tv/membership twitch.tv/tags twitch.tv/commands")

    self.on_connect()

  def join_channel(self, name : str):
    name = name.removeprefix('#').lower()
    if not name in self._channels:
      self.send("JOIN #%s" % name)
      new_channel = libtwitch.IrcChannel(self, name)
      self._channels[name] = new_channel
      self.on_channel_join(new_channel)

    return self._channels[name]

  def part_channel(self, channel : Union[str, libtwitch.IrcChannel]) -> bool:
    if not channel.name in self._channels:
      return False
    self.on_channel_part(channel)
    self._channels.pop(channel.name)
    self.send("PART %s" % channel.name)
    return True

  def send(self, content : str) -> None:
    self.on_raw_egress(content)
    with self._egress_queue_lock:
      self._egress_queue.put(content)

  def chat(self, channel_name : str, text : str) -> None:
    self.send("PRIVMSG #%s :%s" % (channel_name, text))

  @staticmethod
  def _parse_tags(tags_str : str) -> dict[str, str]:
    tags : dict = {}
    tags_parts = tags_str.split(';')

    for tags_part in tags_parts:
      parts = tags_part.split('=')
      if len(parts) != 2:
        continue

      key = parts[0]
      value = parts[1]

      tags[key] = value

    return tags

  def _handle_message(self, match) -> None:
    tags_str = match[1]
    username = match[2]
    channel_name = match[3]
    text = match[4].strip()
    if not channel_name in self._channels:
      return
    channel = self._channels[channel_name]
    tags = self._parse_tags(tags_str)
    channel.handle_privmsg(username, text, tags)

  def _handle_join(self, match):
    username = match[1]
    channelname = match[2]
    if not channelname in self._channels:
      return
    channel = self._channels[channelname]
    channel.handle_join(username)

  def _handle_part(self, match):
    username = match[1]
    channelname = match[2]
    if not channelname in self._channels:
      return
    channel = self._channels[channelname]
    channel.handle_part(username)

  def _handle_roomstate(self, match):
    tags_str = match[1]
    channel_name = match[2]
    if not channel_name in self._channels:
      return
    channel = self._channels[channel_name]
    tags = self._parse_tags(tags_str)
    channel.handle_roomstate(tags)

  def _handle_usernotice(self, match):
    tags_str = match[1]
    channel_name = match[2]
    text = None
    if match[3] is not None:
      text = match[3].strip()

    if not channel_name in self._channels:
      return
    channel = self._channels[channel_name]
    tags = self._parse_tags(tags_str)
    channel.handle_usernotice(text, tags)

  def _read_line(self) -> str:
    if len(self._back_buffer) == 0 or (len(self._back_buffer) == 1 and not self._back_buffer[0].endswith(b'\n')):
      buffer = self._socket.recv(1024)
      self._back_buffer = buffer.split(b'\r\n')

    line = self._back_buffer[0]
    self._back_buffer.pop(0)
    return line.decode("utf-8")

  def _handle_response(self, response):
    self.on_raw_ingress(response)
    message_match = re.match(RE_CHAT_MSG, response)
    if response == "PING :tmi.twitch.tv":  # On Ping
      self.send("PONG :tmi.twitch.tv")
      return
    if message_match is not None:  # On Message
      self._handle_message(message_match)
    else:  # Other message
      join_match = re.match(RE_JOIN, response)
      part_match = re.match(RE_PART, response)
      roomstate_match = re.match(RE_ROOMSTATE, response)
      usernotice_match = re.match(RE_USERNOTICE, response)
      if join_match is not None:  # On Join
        self._handle_join(join_match)
      elif part_match is not None:  # On Part
        self._handle_part(part_match)
      elif roomstate_match is not None:
        self._handle_roomstate(roomstate_match)
      elif usernotice_match is not None:
        self._handle_usernotice(usernotice_match)
      else:
        self.on_unknown(response)

  def _ingress_thread_func(self):
    # TODO: Error
    while self._running:
      response = self._read_line()
      self._handle_response(response)

  def _egress_thread_func(self):
    while self._running:
      # TODO: Maybe this could lead to a race condition?
      item = self._egress_queue.get()
      with self._egress_queue_lock:
        self._socket.send("{}\r\n".format(item).encode("utf-8"))
        self._egress_queue.task_done()
      sleep(1 / self.rate)

  def start(self, rate = RATE_USER):
    if self._running:
      return False
    self.rate = rate
    self._running = True
    self._ingress_thread = threading.Thread(target=self._ingress_thread_func)
    self._egress_thread = threading.Thread(target=self._egress_thread_func)
    self._ingress_thread.start()
    self._egress_thread.start()
    return True

  def stop(self):
    if not self._running:
      return False
    self._running = False
    self._ingress_thread.join()
    self._egress_thread.join()
    return True

  @property
  def is_running(self) -> bool:
    return self._running

  def on_ready(self):
    pass

  def on_destruct(self):
    pass

  def on_raw_ingress(self, data : str):
    pass

  def on_raw_egress(self, data : str):
    pass

  def on_error(self, error : str):
    pass

  def on_unknown(self, data : str):
    pass

  def on_connect(self):
    pass

  def on_disconnect(self):
    pass

  def on_channel_join(self, channel : libtwitch.IrcChannel):
    pass

  def on_channel_part(self, channel : libtwitch.IrcChannel):
    pass

  def on_join(self, join_event : libtwitch.ChatEvent):
    pass

  def on_part(self, part_event : libtwitch.ChatEvent):
    pass

  def on_privmsg(self, msg : libtwitch.IrcMessage):
    pass

  def on_roomstate(self, channel : libtwitch.IrcChannel, tags : dict[str, str]):
    pass

def _update_chatter_type_enum(chatter : libtwitch.IrcChatter, chatter_type : libtwitch.ChatterType, value : bool) -> None:
  if value:
    chatter.type |= chatter_type
  else:
    chatter.type &= ~chatter_type

def _update_chatter_tags(chatter : libtwitch.IrcChatter, tags : dict[str, str]) -> None:
  if "display-name" in tags:
    chatter._display = tags["display-name"]
  if "user-id" in tags:
    chatter.id = int(tags["user-id"])
  if "mod" in tags:
    _update_chatter_type_enum(chatter, libtwitch.ChatterType.Moderator, tags["mod"] == "1")
  if "badges" in tags:
    badges = tags["badges"]
    _update_chatter_type_enum(chatter, libtwitch.ChatterType.Twitch, "admin" in badges or "global_mod" in badges or "staff" in badges)
    _update_chatter_type_enum(chatter, libtwitch.ChatterType.Broadcaster, "broadcaster" in badges)
    _update_chatter_type_enum(chatter, libtwitch.ChatterType.Subscriber, "subscriber" in badges)
    _update_chatter_type_enum(chatter, libtwitch.ChatterType.Turbo, "turbo" in badges)

    if not "mod" in tags:
      _update_chatter_type_enum(chatter, libtwitch.ChatterType.Moderator, "moderator" in badges)
