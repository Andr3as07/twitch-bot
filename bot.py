from dotenv import load_dotenv
from enum import IntFlag, unique
from time import sleep
import socket
import os
import re
import time

HOST = "irc.twitch.tv"
PORT = 6667
RATE = 20 / 30  # messages per second

RE_TAG_PART = r"(?:@([^\s=;]+=[^\s;]*(?:;(?:[^\s=;]+=[^\s;]*))*))?\s?"
RE_CHAT_MSG = r"^%s:([^\s!]+)!(?:[^\s@]+)@(?:[^\s\.]+)(?:\.tmi\.twitch\.tv PRIVMSG) #([^\s!]+) :(.+)$" % RE_TAG_PART
RE_JOIN = r"^:([^\s!]+)!(?:[^\s@]+)@(?:[^\s\.]+)(?:\.tmi\.twitch\.tv JOIN) #([^\s!]+)$"
RE_PART = r"^:([^\s!]+)!(?:[^\s@]+)@(?:[^\s\.]+)(?:\.tmi\.twitch\.tv PART) #([^\s!]+)$"

@unique
class UserType(IntFlag):
  Unknown = 0x00
  Twitch = 0x01
  Broadcaster = 0x02
  Moderator = 0x04
  Founder = 0x08
  Subscriber = 0x10
  VIP = 0x20
  Turbo = 0x40

class Bot:
  def __init__(self, nickname, token):
    self.nickname = nickname.lower()
    self._token = token
    self._socket = None
    self._channels = {}
    self._back_buffer = []

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

  def join_channel(self, name):
    name = name.removeprefix('#').lower()
    if not name in self._channels:
      self._socket.send("JOIN #{}\r\n".format(name).encode("utf-8")) # TODO: Move to join_channel
      new_channel = Channel(self, name)
      self._channels[name] = new_channel
      self.on_channel_join(new_channel)

    return self._channels[name]

  def part_channel(self, channel):
    if not channel.name in self._channels:
      return
    self.on_channel_part(channel)
    self._channels.pop(channel.name)
    self.send("PART %s" % channel.name)

  def send(self, content):
    self._socket.send("{}\r\n".format(content).encode("utf-8"))

  def chat(self, channel_name, text):
    self.send("PRIVMSG #%s :%s" % (channel_name, text))

  def _parse_tags(self, tags_str):
    tags = {}
    tags_parts = tags_str.split(';')

    for tags_part in tags_parts:
      parts = tags_part.split('=')
      if len(parts) != 2:
        continue

      key = parts[0]
      value = parts[1]

      tags[key] = value

    return tags

  def _handle_message(self, match):
    tags_str = match[1]
    username = match[2]
    channelname = match[3]
    text = match[4].strip()
    if not channelname in self._channels:
      return
    channel = self._channels[channelname]
    tags = self._parse_tags(tags_str)
    channel.handle_message(username, text, tags)

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

  def _read_line(self):
    if len(self._back_buffer) == 0 or (len(self._back_buffer) == 1 and not self._back_buffer[0].endswith(b'\n')):
      buffer = self._socket.recv(1024)
      self._back_buffer = buffer.split(b'\r\n')

    line = self._back_buffer[0]
    self._back_buffer.pop(0)
    return line.decode("utf-8")

  def run(self):
    global RATE

    # TODO: Handle CLEARCHAT, CLEARMSG, HOSTTARGET, NOTICE, RECONNECT, ROOMSTATE, USERNOTICE, USERSTATE
    while True:
      response = self._read_line()
      self.on_raw_data(response)
      if response == "PING :tmi.twitch.tv": # On Ping
        self.send("PONG :tmi.twitch.tv")
      else: # Other Message
        message_match = re.match(RE_CHAT_MSG, response)
        if message_match is not None: # On Message
          self._handle_message(message_match)
        else: # Unknown message
          join_match = re.match(RE_JOIN, response)
          part_match = re.match(RE_PART, response)
          if join_match is not None: # On Join
            self._handle_join(join_match)
          elif part_match is not None: # On Part
            self._handle_part(part_match)
          else:
            self.on_error(response)

      sleep(0.01)

  def on_ready(self):
    pass

  def on_destruct(self):
    pass

  def on_raw_data(self, data):
    pass

  def on_error(self, error):
    pass

  def on_connect(self):
    pass

  def on_channel_join(self, channel):
    pass

  def on_channel_part(self, channel):
    pass

  def on_join(self, join_event):
    pass

  def on_part(self, part_event):
    pass

  def on_message(self, msg):
    pass

def _update_chatter_type_enum(chatter, type, value):
  if value:
    chatter.type |= type
  else:
    chatter.type &= ~type

def _update_chatter_tags(chatter, tags):
  if "display-name" in tags:
    chatter._display = tags["display-name"]
  if "user-id" in tags:
    chatter.id = int(tags["user-id"])
  if "mod" in tags:
    _update_chatter_type_enum(chatter, UserType.Moderator, tags["mod"] == "1")
  if "badges" in tags:
    badges = tags["badges"]
    _update_chatter_type_enum(chatter, UserType.Twitch, "admin" in badges or "global_mod" in badges or "staff" in badges)
    _update_chatter_type_enum(chatter, UserType.Broadcaster, "broadcaster" in badges)
    _update_chatter_type_enum(chatter, UserType.Subscriber, "subscriber" in badges)
    _update_chatter_type_enum(chatter, UserType.Turbo, "turbo" in badges)

    if not "mod" in tags:
      _update_chatter_type_enum(chatter, UserType.Moderator)

class Channel:
  def __init__(self, connection, name):
    self._connection = connection
    self.name = name
    self._chatters = {}

  def leave(self):
    self._connection.leave_channel(self)

  def chat(self, text):
    self._connection.chat(self.name, text)

  def ban(self, user, reason=None):
    if isinstance(user, Chatter):
      user = user.name

    if reason is None:
      self.chat(".ban %s" % user)
    else:
      self.chat(".ban %s %s" % (user, reason))

  def timeout(self, user, time, reason=None):
    if isinstance(user, Chatter):
      user = user.name

    if time < 0:
      return False

    if reason is None:
      self.chat(".timeout %s %s" % (user, time))
    else:
      self.chat(".timeout %s %s %s" % (user, time, reason))

  def clear(self):
    self.chat(".clear")

  def get_chatter(self, user_name):
    if user_name in self._chatters:
      return self._chatters[user_name]
    return None

  def handle_message(self, author_name, text, tags):
    chatter = self.get_chatter(author_name)
    if chatter is None:
      chatter = Chatter(self, author_name)
      self._chatters[author_name] = chatter

    _update_chatter_tags(chatter, tags)

    msg = Message(self, chatter, text, tags)

    if "id" in tags:
      msg.id = tags["id"]

    self._connection.on_message(msg)

  def handle_join(self, name):
    chatter = self.get_chatter(name)
    if chatter is None:
      chatter = Chatter(self, name)
      self._chatters[name] = chatter
    self._connection.on_join(ChatEvent(self, chatter))

  def handle_part(self, name):
    chatter = self.get_chatter(name)
    if chatter is None:
      chatter = Chatter(self, name)
      self._chatters[name] = chatter
    self._connection.on_part(ChatEvent(self, chatter))

  def __str__(self):
    return self.name

  def __repr__(self):
    return str(self)

class Chatter:
  def __init__(self, channel, name):
    self.channel = channel
    self.name = name
    self._display = None
    self.id = None
    self.type = UserType.Unknown

  def has_type(self, other):
    return (int(self.type) & ~other) != 0

  @property
  def display_name(self):
    if self._display is not None:
      return self._display
    return self.name

  def timeout(self, time, reason = None):
    self.channel.timeout(self, time, reason)

  def ban(self, reason = None):
    self.channel.ban(self, reason)

  def __str__(self):
    return "%s#%s(%s)" % (self.display_name, self.id, self.type)

  def __repr__(self):
    return str(self)

class Message:
  def __init__(self, channel, author, text, tags):
    self.timestamp = time.time()
    self.channel = channel
    self.author = author
    self.text = text
    self.tags = tags
    self.id = None

  def delete(self):
    self.channel.chat(".delete %s" % self.id)

class ChatEvent:
  def __init__(self, channel, user):
    self.channel = channel
    self.user = user

if __name__ == '__main__':
  load_dotenv()
  bot = Bot("whyamitalking", os.getenv('CHAT_TOKEN'))
  bot.connect()
  channel = bot.join_channel("Andr3as07")
  bot.run()
