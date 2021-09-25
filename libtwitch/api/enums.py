from enum import Enum, IntEnum, unique

@unique
class RequestPriority(IntEnum):
  High = 0
  Medium = 10
  Low = 20

@unique
class RequestRatelimitBehaviour(IntEnum):
  Mandatory = 0
  Optional = 1

@unique
class RequestCacheBehaviour(IntEnum):
  NoCache = 0
  CacheOnRatelimit = 3
  CacheOnFail = 4
  CacheFirst = 5

@unique
class BroadcasterType(Enum):
  Nothing = ""
  Affiliate = "affiliate"
  Partner = "partner"

@unique
class UserType(Enum):
  Nothing = ""
  GlobalMod = "global_mod"
  Admin = "admin"
  Staff = "staff"
