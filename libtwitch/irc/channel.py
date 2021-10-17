from __future__ import annotations

from typing import Optional, Union

import libtwitch
import libtwitch.irc.connection
from libtwitch.irc.enums import SubEventType, SubGiftEventType, str2ritual, str2subtier
from libtwitch.irc.events import ChatEvent, RaidEvent, RitualEvent, SubEvent, SubGiftEvent
from libtwitch.irc.message import MessageEvent

class IrcChannel:
  def __init__(self, connection : libtwitch.IrcConnection, name : str):
    self._connection = connection
    self._id : Optional[int] = 0
    self._name = name
    self._emote_only = False
    self._follower_only : int = -1
    self._subs_only = False
    self._slow = 0
    self._r9k : bool = False
    self._chatters = {}
    self._tags : dict[str, str] = {}

  @property
  def is_emote_only(self) -> bool:
    return self._emote_only

  @property
  def is_subs_only(self) -> bool:
    return self._subs_only

  @property
  def is_followers_only(self) -> bool:
    return self._follower_only >= 0

  @property
  def get_folowers_only_minutes(self) -> int:
    return self._follower_only

  @property
  def is_slow_mode(self) -> bool:
    return self._slow > 0

  @property
  def get_slow_mode_seconds(self) -> int:
    return self._slow

  @property
  def is_in_r9k_mode(self) -> bool:
    return self._r9k

  @property
  def name(self) -> str:
    return self._name

  @property
  def id(self) -> Optional[int]:
    if self._id is None or self._id < 0:
      return None
    return self._id

  @property
  def tags(self) -> dict[str, str]:
    return self._tags

  def part(self) -> None:
    self._connection.part_channel(self)

  def chat(self, text : str) -> None:
    self._connection.chat(self._name, text)

  def ban(self, user : Union[libtwitch.IrcChatter, str], reason : str = None) -> None:
    if isinstance(user, libtwitch.IrcChatter):
      user = user.login

    if reason is None:
      self.chat(".ban %s" % user)
    else:
      self.chat(".ban %s %s" % (user, reason))

  def timeout(self, user : Union[libtwitch.IrcChatter, str], duration : int, reason : str = None):
    if isinstance(user, libtwitch.IrcChatter):
      user = user.login

    if duration < 0:
      return False

    if reason is None:
      self.chat(".timeout %s %s" % (user, duration))
    else:
      self.chat(".timeout %s %s %s" % (user, duration, reason))

  def clear(self):
    self.chat(".clear")

  def get_chatter(self, user_name : str) -> Optional[libtwitch.IrcChatter]:
    if user_name in self._chatters:
      return self._chatters[user_name]
    return None

  def handle_privmsg(self, author_name : str, text : str, tags : dict[str, str], event: Optional[MessageEvent] = None):
    chatter = self.get_chatter(author_name)
    if chatter is None:
      chatter = libtwitch.IrcChatter(self, author_name)
      self._chatters[author_name] = chatter

    _update_chatter_tags(chatter, tags) # TODO: FIXME

    msg = libtwitch.IrcMessage(self, chatter, text, tags)

    if "id" in msg.tags:
      msg._id = msg.tags["id"]

    if event is not None:
      msg._event = event

    self._connection.on_privmsg(msg)

  def handle_join(self, name : str):
    chatter = self.get_chatter(name)
    if chatter is None:
      chatter = libtwitch.IrcChatter(self, name)
      self._chatters[name] = chatter
    ev = ChatEvent()
    ev.channel = self
    ev.chatter = chatter

    self._connection.on_join(ev)

  def handle_part(self, name : str):
    chatter = self.get_chatter(name)
    if chatter is None:
      chatter = libtwitch.IrcChatter(self, name)
      self._chatters[name] = chatter
    ev = ChatEvent()
    ev.channel = self
    ev.chatter = chatter

    self._connection.on_part(ev)

  def __eq__(self, other):
    return self._name == other.login

  def __hash__(self):
    return hash(self._name)

  def __str__(self):
    return "#%s" % self._name

  def __repr__(self):
    return "<Channel name: %s>" % self._name

  def handle_roomstate(self, tags : dict[str, str]):
    if "emote-only" in tags:
      self._emote_only = tags["emote-only"] == "1"
    if "followers-only" in tags:
      self._follower_only = int(tags["followers-only"])
    if "r9k" in tags:
      self._r9k = tags["r9k"] == "1"
    if "slow" in tags:
      self._slow = int(tags["slow"])
    if "subs-only" in tags:
      self._subs_only = tags["subs-only"] == "1"
    if "room-id" in tags:
      self._id = int(tags["room-id"])
    self._connection.on_roomstate(self, tags)
    self._tags = tags

  def _hande_sub(self, text, tags, typ : SubEventType): # sub and resub
    ev = SubEvent(typ)
    ev.total_months = int(tags['msg-param-cumulative-months'])
    ev.streak_share = bool(tags['msg-param-should-share-streak'])
    ev.streak_months = int(tags['msg-param-streak-months'])
    ev.tier = str2subtier(tags['msg-param-sub-plan'])
    ev.tier_name = tags['msg-param-sub-plan-name']

    author_name = tags['login']

    self.handle_privmsg(author_name, text, tags, ev)

  def _handle_subgift(self, tags, typ : SubGiftEventType): # subgift and anon-subgift
    ev = SubGiftEvent(typ)
    ev.total_months = int(tags['msg-param-months'])
    ev.recipient_display = tags['msg-param-recipient-display-name']
    ev.recipient_id = tags['msg-param-recipient-id']
    if 'msg-param-recipient-name' in tags:
      ev.recipient_login = tags['msg-param-recipient-name']
    elif 'msg-param-recipient-user-name' in tags:
      ev.recipient_login = tags['msg-param-recipient-user-name']
    ev.tier_str = str2subtier(tags['msg-param-sub-plan'])
    ev.tier_name = tags['msg-param-sub-plan-name']
    if 'msg-param-gift-months' in tags:
      ev.gift_months = int(tags['msg-param-gift-months'])

    ev.tags = tags
    ev.channel = self

    self._connection.on_subgift(ev)

  def _handle_submysterygift(self, text, tags):
    assert False, "unimplemented"
    pass

  def _handle_rewardgift(self, text, tags):
    assert False, "unimplemented"
    pass

  def _handle_raid(self, tags):
    ev = RaidEvent()
    ev.display = tags['msg-param-displayName']
    ev.login = tags['msg-param-login']
    ev.viewers = int(tags['msg-param-viewerCount'])

    ev.tags = tags
    ev.channel = self

    self._connection.on_raid(ev)

  def _handle_unraid(self, tags):
    assert False, "unimplemented"
    pass

  def _handle_giftpaidupgrade(self, text, tags): # giftpaidupgrade and anon-giftpaidupgrade
    total = int(tags['msg-param-promo-gift-total'])
    promo_name = tags['msg-param-promo-name']
    login = tags['msg-param-sender-login']
    display = tags['msg-param-sender-name']
    # TODO: Parse
    # TODO: event
    assert False, "unimplemented"
    pass

  def _handle_ritual(self, text, tags): # ritual
    ev = RitualEvent()
    ev.tags = tags
    ev.channel = self
    ev.typ = str2ritual(tags['msg-param-ritual-name'])

    self._connection.on_ritual(ev)

  def _handle_bitsbadgetier(self, text, tags):
    threshold = tags['msg-param-threshold']
    # TODO: event
    assert False, "unimplemented"
    pass

  def handle_usernotice(self, text, tags):
    if not "msg-id" in tags:
      return

    msg_type = tags["msg-id"]
    if msg_type == "sub" :
      self._hande_sub(text, tags, SubEventType.Sub)
    elif msg_type == "resub":
      self._hande_sub(text, tags, SubEventType.Resub)
    elif msg_type == "subgift":
      self._handle_subgift(tags, SubGiftEventType.SubGift)
    elif msg_type == "anonsubgift":
      self._handle_subgift(tags, SubGiftEventType.AnonSubGift)
    elif msg_type == "submysterygift":
      self._handle_submysterygift(text, tags)
    elif msg_type == "giftpaidupgrade" or msg_type == "anongiftpaidupgrade":
      self._handle_giftpaidupgrade(text, tags)
    elif msg_type == "rewardgift":
      self._handle_rewardgift(text, tags)
    elif msg_type == "raid":
      self._handle_raid(tags)
    elif msg_type == "unraid":
      self._handle_unraid(tags)
    elif msg_type == "ritual":
      self._handle_ritual(text, tags)
    elif msg_type == "bitsbadgetier":
      self._handle_bitsbadgetier(text, tags)
    else:
      print("Unknown usernotice type %s" % msg_type)

def _update_chatter_type_enum(chatter : libtwitch.IrcChatter, chatter_type : libtwitch.ChatterType, value : bool) -> None:
  if value:
    chatter._type |= chatter_type
  else:
    chatter._type &= ~chatter_type

def _update_chatter_tags(chatter : libtwitch.IrcChatter, tags : dict[str, str]) -> None:
  if "display-name" in tags:
    chatter._display = tags["display-name"]
  if "user-id" in tags:
    chatter._id = int(tags["user-id"])
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
