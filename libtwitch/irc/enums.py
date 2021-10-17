from enum import Enum, IntFlag, auto, unique

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

@unique
class SubscriptionTier(Enum):
  Prime = 0
  Tier1 = 1000
  Tier2 = 2000
  Tier3 = 3000

def str2subtier(text: str) -> SubscriptionTier:
  if text == 'Prime':
    return SubscriptionTier.Prime
  elif text == '1000':
    return SubscriptionTier.Tier1
  elif text == '2000':
    return SubscriptionTier.Tier2
  elif text == '3000':
    return SubscriptionTier.Tier3
  else:
    assert False, 'unreachable'

@unique
class SubGiftEventType(Enum):
  SubGift = auto()
  AnonSubGift = auto()

@unique
class SubEventType(Enum):
  Sub = auto()
  Resub = auto()

@unique
class RitualType(Enum):
  NewChatter = auto()

def str2ritual(text: str) -> RitualType:
  if text == 'new_chatter':
    return RitualType.NewChatter
  else:
    assert False, 'unreachable'