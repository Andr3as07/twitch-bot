from __future__ import annotations

from dataclasses import dataclass

import libtwitch

@dataclass
class ChatEvent:
  def __init__(self, _channel : libtwitch.IrcChannel, _chatter : libtwitch.IrcChatter):
    self.channel = _channel
    self.chatter = _chatter

@dataclass
class SubEvent:
  total_months : int = 0
  streak_share : bool = False
  streak_months : int = 0
  tier : libtwitch.SubscriptionTier = libtwitch.SubscriptionTier.Prime
  tier_name : str = "Prime"

@dataclass
class SubGiftEvent:
  total_months : int = 0
  recipient_display : str = None
  recipient_id : str = None
  recipient_login : str = None
  tier : libtwitch.SubscriptionTier = libtwitch.SubscriptionTier.Prime
  tier_name : str = "Prime"
  gift_months : int = 0

@dataclass
class RaidEvent:
  def __init__(self, login : str, display : str, viewers : int):
    self.display = display
    self.login = login
    self.viewers = viewers

  display : str = None
  login : str = None
  viewers : int = 0