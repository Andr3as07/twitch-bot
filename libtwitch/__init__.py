__title__ = 'Twitch'
__author__ = 'Andr3as07'

__version__ = '1.0.0'

__path__ = __import__('pkgutil').extend_path(__path__, __name__)

from .core import Connection, ChatterType, Channel, Chatter, Message, ChatEvent, RATE_USER, RATE_MODERATOR
from .cog import Cog, CogEvent
from .bot import Bot
