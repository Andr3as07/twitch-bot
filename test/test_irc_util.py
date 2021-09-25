import unittest

from libtwitch import ChatterType, IrcChatter
from libtwitch.irc.util import update_chatter_type_enum

class TestIrcUtil(unittest.TestCase):
  def test_update_type_enum(self):
    # Setup
    chatter = IrcChatter(None, "dummy")

    # Positive
    update_chatter_type_enum(chatter, ChatterType.Moderator, True)
    self.assertFalse(chatter.type & ChatterType.Moderator == 0)

    # Negative
    update_chatter_type_enum(chatter, ChatterType.Moderator, False)
    self.assertTrue(chatter.type & ChatterType.Moderator == 0)

