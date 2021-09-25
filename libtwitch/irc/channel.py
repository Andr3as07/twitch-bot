from __future__ import annotations

from typing import Optional, Union

import libtwitch
import libtwitch.irc.connection

class IrcChannel:
  def __init__(self, connection : libtwitch.IrcConnection, name : str):
    self._connection = connection
    self.name = name
    self.emote_only = False
    self.follower_only : int = -1
    self.subs_only = False
    self.slow = 0
    self.r9k = 0
    self._chatters = {}
    self.tags = {}

  def part(self) -> None:
    self._connection.part_channel(self)

  def chat(self, text : str) -> None:
    self._connection.chat(self.name, text)

  def ban(self, user : Union[libtwitch.IrcChatter, str], reason : str = None) -> None:
    if isinstance(user, libtwitch.IrcChatter):
      user = user.name

    if reason is None:
      self.chat(".ban %s" % user)
    else:
      self.chat(".ban %s %s" % (user, reason))

  def timeout(self, user : Union[libtwitch.IrcChatter, str], duration : int, reason : str = None):
    if isinstance(user, libtwitch.IrcChatter):
      user = user.name

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

  def handle_privmsg(self, author_name : str, text : str, tags : dict[str, str]):
    chatter = self.get_chatter(author_name)
    if chatter is None:
      chatter = libtwitch.IrcChatter(self, author_name)
      self._chatters[author_name] = chatter

    libtwitch.irc.connection._update_chatter_tags(chatter, tags) # TODO: FIXME

    msg = libtwitch.IrcMessage(self, chatter, text, tags)

    if "id" in tags:
      msg.id = tags["id"]

    self._connection.on_privmsg(msg)

  def handle_join(self, name : str):
    chatter = self.get_chatter(name)
    if chatter is None:
      chatter = libtwitch.IrcChatter(self, name)
      self._chatters[name] = chatter
    self._connection.on_join(libtwitch.ChatEvent(self, chatter))

  def handle_part(self, name : str):
    chatter = self.get_chatter(name)
    if chatter is None:
      chatter = libtwitch.IrcChatter(self, name)
      self._chatters[name] = chatter
    self._connection.on_part(libtwitch.ChatEvent(self, chatter))

  def __str__(self):
    return self.name

  def __repr__(self):
    return str(self)

  def handle_roomstate(self, tags : dict[str, str]):
    if "emote-only" in tags:
      self.emote_only = tags["emote-only"] == "1"
    if "followers-only" in tags:
      self.follower_only = int(tags["followers-only"])
    if "r9k" in tags:
      self.r9k = tags["r9k"] == "1"
    if "slow" in tags:
      self.slow = int(tags["slow"])
    if "subs-only" in tags:
      self.subs_only = tags["subs-only"] == "1"
    self._connection.on_roomstate(self, tags)
    self.tags = tags

  def _hande_sub(self, text, tags): # sub and resub
    total_months = int(tags['msg-param-cumulative-months'])
    streak_share = bool(tags['msg-param-should-share-streak'])
    streak_months = int(tags['msg-param-streak-months'])
    tier_str = tags['msg-param-sub-plan']
    tier_name = tags['msg-param-sub-plan-name']
    # TODO: event
    pass

  def _handle_subgift(self, text, tags): # subgift and anon-subgift
    total_months = int(tags['msg-param-months'])
    recipient_display = tags['msg-param-recipient-display-name']
    recipient_id = tags['msg-param-recipient-id']
    recipient_login = tags['msg-param-recipient-name']
    tier_str = tags['msg-param-sub-plan']
    tier_name = tags['msg-param-sub-plan-name']
    #gift_months = int(tags['msg-param-gift-months'])
    # TODO: event
    pass

  def _handle_submysterygift(self, text, tags):
    pass

  def _handle_rewardgift(self, text, tags):
    pass

  def _handle_raid(self, text, tags):
    display = tags['msg-param-displayName']
    login = tags['msg-param-login']
    viewers = int(tags['msg-param-viewerCount'])
    # TODO: event
    pass

  def _handle_unraid(self, text, tags):
    pass

  def _handle_giftpaidupgrade(self, text, tags): # giftpaidupgrade and anon-giftpaidupgrade
    total = int(tags['msg-param-promo-gift-total'])
    promo_name = tags['msg-param-promo-name']
    login = tags['msg-param-sender-login']
    display = tags['msg-param-sender-name']
    # TODO: Parse
    # TODO: event
    pass

  def _handle_ritual(self, text, tags): # ritual
    ritual_name = tags['msg-param-ritual-name']
    # TODO: event
    pass

  def _handle_bitsbadgetier(self, text, tags):
    threshold = tags['msg-param-threshold']
    # TODO: event
    pass

  def handle_usernotice(self, text, tags):
    if not "msg-id" in tags:
      return

    msg_type = tags["msg-id"]
    if msg_type == "sub" or msg_type == "resub":
      self._hande_sub(text, tags)
    elif msg_type == "subgift" or msg_type == "anonsubgift":
      self._handle_subgift(text, tags)
    elif msg_type == "submysterygift":
      self._handle_submysterygift(text, tags)
    elif msg_type == "giftpaidupgrade" or msg_type == "anongiftpaidupgrade":
      self._handle_giftpaidupgrade(text, tags)
    elif msg_type == "rewardgift":
      self._handle_rewardgift(text, tags)
    elif msg_type == "raid":
      self._handle_raid(text, tags)
    elif msg_type == "unraid":
      self._handle_unraid(text, tags)
    elif msg_type == "ritual":
      self._handle_ritual(text, tags)
    elif msg_type == "bitsbadgetier":
      self._handle_bitsbadgetier(text, tags)
    else:
      print("Unknown usernotice type %s" % msg_type)
