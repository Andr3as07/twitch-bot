__title__ = 'Twitch'
__author__ = 'Andr3as07'

__version__ = '1.0.0'

__path__ = __import__('pkgutil').extend_path(__path__, __name__)

from .core import Connection, ChatterType, Channel, Chatter, Message, ChatEvent, RATE_USER, RATE_MODERATOR
from .plugin import Plugin, PluginEvent
from .bot import Bot
from .moderation_action import ModerationAction, ModerationActionType
from .datastore import Datastore
from .file_datastore import FileDatastore