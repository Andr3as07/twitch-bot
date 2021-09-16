from __future__ import annotations

import threading
from queue import Queue

from enum import IntFlag, unique
from typing import Union
from time import sleep
import socket
import re
import time

HOST = "irc.twitch.tv"
PORT = 6667
RATE_USER = 20 / 30  # messages per second
RATE_MODERATOR = 100 / 30  # messages per second

RE_TAG_PART = r"(?:@([^\s=;]+=[^\s;]*(?:;(?:[^\s=;]+=[^\s;]*))*))?\s?"
RE_CHAT_MSG = r"^%s:([^\s!]+)!(?:[^\s@]+)@(?:[^\s\.]+)(?:\.tmi\.twitch\.tv PRIVMSG) #([^\s!]+) :(.+)$" % RE_TAG_PART
RE_JOIN = r"^:([^\s!]+)!(?:[^\s@]+)@(?:[^\s\.]+)(?:\.tmi\.twitch\.tv JOIN) #([^\s!]+)$"
RE_PART = r"^:([^\s!]+)!(?:[^\s@]+)@(?:[^\s\.]+)(?:\.tmi\.twitch\.tv PART) #([^\s!]+)$"

@unique
class ChatterType(IntFlag):
  Unknown = 0x00
  Twitch = 0x01
  Broadcaster = 0x02
  Moderator = 0x04
  Founder = 0x08
  Subscriber = 0x10
  VIP = 0x20
  Turbo = 0x40

class IrcConnection:
  def __init__(self, nickname, token):
    self.nickname = nickname.lower()
    self._token = token
    self._socket = None
    self._channels = {}
    self._back_buffer = []

    self.rate = RATE_USER
    self._running = False

    self._ingress_thread = None
    self._egress_thread = None

    self._egress_queue = Queue()
    self._egress_queue_lock = threading.Lock()

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
      new_channel = IrcChannel(self, name)
      self._channels[name] = new_channel
      self.on_channel_join(new_channel)

    return self._channels[name]

  def part_channel(self, channel : Union[str, IrcChannel]) -> bool:
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

  def _parse_tags(self, tags_str : str) -> dict[str,str]:
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

  def _read_line(self) -> str:
    if len(self._back_buffer) == 0 or (len(self._back_buffer) == 1 and not self._back_buffer[0].endswith(b'\n')):
      buffer = self._socket.recv(1024)
      self._back_buffer = buffer.split(b'\r\n')

    line = self._back_buffer[0]
    self._back_buffer.pop(0)
    return line.decode("utf-8")

  def _ingress_thread_func(self):
    # TODO: Error
    while self._running:
      response = self._read_line()
      self.on_raw_ingress(response)
      message_match = re.match(RE_CHAT_MSG, response)
      if response == "PING :tmi.twitch.tv": # On Ping
        self.send("PONG :tmi.twitch.tv")
        continue
      if message_match is not None: # On Message
        self._handle_message(message_match)
      else: # Other message
        join_match = re.match(RE_JOIN, response)
        part_match = re.match(RE_PART, response)
        if join_match is not None: # On Join
          self._handle_join(join_match)
        elif part_match is not None: # On Part
          self._handle_part(part_match)
        else:
          self.on_unknown(response)

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

  def on_channel_join(self, channel : IrcChannel):
    pass

  def on_channel_part(self, channel : IrcChannel):
    pass

  def on_join(self, join_event : ChatEvent):
    pass

  def on_part(self, part_event : ChatEvent):
    pass

  def on_privmsg(self, msg : IrcMessage):
    pass

def _update_chatter_type_enum(chatter : IrcChatter, chatter_type : ChatterType, value : bool) -> None:
  if value:
    chatter.type |= chatter_type
  else:
    chatter.type &= ~chatter_type

def _update_chatter_tags(chatter : IrcChatter, tags : dict[str, str]) -> None:
  if "display-name" in tags:
    chatter._display = tags["display-name"]
  if "user-id" in tags:
    chatter.id = int(tags["user-id"])
  if "mod" in tags:
    _update_chatter_type_enum(chatter, ChatterType.Moderator, tags["mod"] == "1")
  if "badges" in tags:
    badges = tags["badges"]
    _update_chatter_type_enum(chatter, ChatterType.Twitch, "admin" in badges or "global_mod" in badges or "staff" in badges)
    _update_chatter_type_enum(chatter, ChatterType.Broadcaster, "broadcaster" in badges)
    _update_chatter_type_enum(chatter, ChatterType.Subscriber, "subscriber" in badges)
    _update_chatter_type_enum(chatter, ChatterType.Turbo, "turbo" in badges)

    if not "mod" in tags:
      _update_chatter_type_enum(chatter, ChatterType.Moderator)

class IrcChannel:
  def __init__(self, connection : IrcConnection, name : str):
    self._connection = connection
    self.name = name
    self._chatters = {}

  def part(self) -> None:
    self._connection.part_channel(self)

  def chat(self, text : str) -> None:
    self._connection.chat(self.name, text)

  def ban(self, user : Union[IrcChatter, str], reason : str = None) -> None:
    if isinstance(user, IrcChatter):
      user = user.name

    if reason is None:
      self.chat(".ban %s" % user)
    else:
      self.chat(".ban %s %s" % (user, reason))

  def timeout(self, user : Union[IrcChatter, str], time : int, reason : str = None):
    if isinstance(user, IrcChatter):
      user = user.name

    if time < 0:
      return False

    if reason is None:
      self.chat(".timeout %s %s" % (user, time))
    else:
      self.chat(".timeout %s %s %s" % (user, time, reason))

  def clear(self):
    self.chat(".clear")

  def get_chatter(self, user_name : str) -> IrcChatter:
    if user_name in self._chatters:
      return self._chatters[user_name]
    return None

  def handle_privmsg(self, author_name : str, text : str, tags : str):
    chatter = self.get_chatter(author_name)
    if chatter is None:
      chatter = IrcChatter(self, author_name)
      self._chatters[author_name] = chatter

    _update_chatter_tags(chatter, tags)

    msg = IrcMessage(self, chatter, text, tags)

    if "id" in tags:
      msg.id = tags["id"]

    self._connection.on_privmsg(msg)

  def handle_join(self, name : str):
    chatter = self.get_chatter(name)
    if chatter is None:
      chatter = IrcChatter(self, name)
      self._chatters[name] = chatter
    self._connection.on_join(ChatEvent(self, chatter))

  def handle_part(self, name : str):
    chatter = self.get_chatter(name)
    if chatter is None:
      chatter = IrcChatter(self, name)
      self._chatters[name] = chatter
    self._connection.on_part(ChatEvent(self, chatter))

  def __str__(self):
    return self.name

  def __repr__(self):
    return str(self)

class IrcChatter:
  def __init__(self, channel : IrcChannel, name : str):
    self.channel : IrcChannel = channel
    self.name : str = name
    self._display : str = None
    self.id : int = None
    self.type : ChatterType = ChatterType.Unknown

  def has_type(self, other : ChatterType) -> bool:
    return (int(self.type) & ~other) != 0

  @property
  def display_name(self) -> str:
    if self._display is not None:
      return self._display
    return self.name

  def timeout(self, time : int, reason : str = None):
    self.channel.timeout(self, time, reason)

  def ban(self, reason : str = None):
    self.channel.ban(self, reason)

  def __str__(self):
    return "%s#%s(%s)" % (self.display_name, self.id, self.type)

  def __repr__(self):
    return str(self)

class IrcMessage:
  def __init__(self, channel : IrcChannel, author : IrcChatter, text : str, tags : dict[str, str]):
    self.timestamp = time.time()
    self.channel = channel
    self.author = author
    self.text = text
    self.tags = tags
    self.id = None

  def delete(self) -> None:
    self.channel.chat(".delete %s" % self.id)

class ChatEvent:
  def __init__(self, channel : IrcChannel, chatter : IrcChatter):
    self.channel = channel
    self.chatter = chatter