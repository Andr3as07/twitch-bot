from enum import Enum, IntFlag, unique

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