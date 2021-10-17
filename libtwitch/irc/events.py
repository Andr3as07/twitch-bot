from __future__ import annotations

from dataclasses import dataclass

import libtwitch
from libtwitch.irc.enums import RitualType, SubEventType, SubGiftEventType

@dataclass
class ChannelEvent:
  tags : dict[str, str] = None
  channel : libtwitch.IrcChannel = None

@dataclass
class MessageEvent:
  pass

@dataclass
class ChatEvent(ChannelEvent):
  chatter : libtwitch.IrcChatter = None

@dataclass
class SubEvent(MessageEvent):
  def __init__(self, typ : SubEventType):
    self.typ = typ

  typ : SubEventType = SubEventType.Sub
  total_months : int = 0
  streak_share : bool = False
  streak_months : int = 0
  tier : libtwitch.SubscriptionTier = libtwitch.SubscriptionTier.Prime
  tier_name : str = "Prime"

@dataclass
class SubGiftEvent(ChannelEvent):
  def __init__(self, typ : SubGiftEventType):
    self.typ = typ

  typ : SubGiftEventType = SubGiftEventType.SubGift
  total_months : int = 0
  recipient_display : str = None
  recipient_id : str = None
  recipient_login : str = None
  tier : libtwitch.SubscriptionTier = libtwitch.SubscriptionTier.Prime
  tier_name : str = "Prime"
  gift_months : int = -1

@dataclass
class RaidEvent(ChannelEvent):
  display : str = None
  login : str = None
  viewers : int = 0

@dataclass
class RitualEvent(ChannelEvent):
  typ : RitualType = RitualType.NewChatter
