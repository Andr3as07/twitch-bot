from __future__ import annotations
from enum import Enum, IntEnum, auto

from libtwitch import Bot, BotMessage, ChatEvent, ChatterType, IrcChatter, Plugin

ESCAPE = ""

class TerminalType(Enum):
  ANSI = auto()
  Win32 = auto()

  Debug = auto()
  Other = auto()

class ConsoleColor(IntEnum):
  Black = 30
  Red = 31
  Green = 32
  Yellow = 33
  Blue = 34
  Purple = 35
  Cyan = 36
  White = 37

class ConsoleStyle(IntEnum):
  Normal = 0
  Bold = 1
  Underline = 2
  Bright = 4
  Dim = 8
  Blink = 16

class ConsoleTextBuilder:
  def __init__(self, terminal_type : TerminalType = TerminalType.ANSI):
    self._text = ""
    self._current_foreground_color = ConsoleColor.White
    self._current_background_color = ConsoleColor.Black
    self._current_style = ConsoleStyle.Normal
    self._terminal_type : TerminalType = terminal_type

  def __str__(self):
    return self._text

  def __repr__(self):
    return str(self)

  def _get_fg_color_code(self, color : ConsoleColor) -> str:
    # TODO: Win32
    if self._terminal_type == TerminalType.ANSI:
      return self._get_fg_color_code_ansi(color)
    elif self._terminal_type == TerminalType.Debug:
      return self._get_fg_color_code_debug(color)
    else:
      return ""

  def _get_bg_color_code(self, color : ConsoleColor) -> str:
    # TODO: Win32
    if self._terminal_type == TerminalType.ANSI:
      return self._get_bg_color_code_ansi(color)
    elif self._terminal_type == TerminalType.Debug:
      return self._get_bg_color_code_debug(color)
    else:
      return ""

  def _get_fg_color_code_ansi(self, color : ConsoleColor) -> str:
    code = "%s[" % ESCAPE
    if self._current_style & ConsoleStyle.Bold != 0:
      code += "1;"
    elif self._current_style & ConsoleStyle.Dim != 0:
      code += "2;"
    elif self._current_style & ConsoleStyle.Blink != 0:
      code += "5;"
    elif self._current_style & ConsoleStyle.Underline != 0:
      code += "4;"
    else:
      code += "0;"

    number = int(color)
    if self._current_style & ConsoleStyle.Bright != 0:
      number += 60
    code += str(number)

    code += "m"

    return code

  def _get_fg_color_code_debug(self, color : ConsoleColor) -> str:
    return "<fg:%s>" % color.name

  def _get_bg_color_code_ansi(self, color : ConsoleColor) -> str:
    code = "%s[" % ESCAPE
    if self._current_style & ConsoleStyle.Bright != 0:
      code += "0;"

    number = int(color) + 10
    if self._current_style & ConsoleStyle.Bright != 0:
      number += 60
    code += str(number)

    code += "m"

    return code

  def _get_bg_color_code_debug(self, color : ConsoleColor) -> str:
    return "<bg:%s>" % color.name

  def fg(self, color : ConsoleColor) -> ConsoleTextBuilder:
    self._current_foreground_color = color
    self._text += self._get_fg_color_code(color)
    return self

  def bg(self, color : ConsoleColor) -> ConsoleTextBuilder:
    self._current_background_color = color
    self._text += self._get_bg_color_code(color)
    return self

  def style(self, style : ConsoleStyle) -> ConsoleTextBuilder:
    self._current_style = style
    return self

  def text(self, text: str, fg : ConsoleColor = None, bg : ConsoleColor = None, style : ConsoleStyle = None) -> ConsoleTextBuilder:
    if style is not None:
      self.style(style)
    if fg is not None:
      self.fg(fg)
    if bg is not None:
      self.bg(bg)
    # TODO: Emit color if the style was changed and no new color was set
    self._text += text
    return self

  def reset(self) -> ConsoleTextBuilder:
    # TODO: Win32
    if self._terminal_type == TerminalType.Debug:
      self._text += "<reset>"
    elif self._terminal_type == TerminalType.ANSI:
      self._text += "%s[0m" % ESCAPE
    elif self._terminal_type == TerminalType.Other:
      pass
    self._current_style = ConsoleStyle.Normal
    self._current_foreground_color = ConsoleColor.White
    self._current_background_color = ConsoleColor.Black
    return self

class UtilConsole(Plugin):
  name = "util.console"
  def __init__(self, bot):
    super().__init__(bot)
    self.include_channel_name = False

  def _chatter_color(self, chatter : IrcChatter) -> ConsoleColor:
    if chatter.login == chatter.channel.name or chatter.has_type(ChatterType.Broadcaster):
      return ConsoleColor.Red
    elif chatter.has_type(ChatterType.Moderator):
      return ConsoleColor.Cyan
    elif chatter.has_type(ChatterType.VIP):
      return ConsoleColor.Yellow
    elif chatter.has_type(ChatterType.Subscriber):
      return ConsoleColor.Green
    elif chatter.has_type(ChatterType.Twitch):
      return ConsoleColor.Purple
    #elif chatter.has_type(ChatterType.Follower):
    #  return ConsoleColor.Blue
    else:
      return ConsoleColor.White

  def _get_chatter_text(self, chatter : IrcChatter) -> str:
    builder = ConsoleTextBuilder().text(chatter.display_name, fg=self._chatter_color(chatter))
    if self.include_channel_name:
      builder.reset().text("@").text(chatter.channel.name)
    return str(builder.reset())

  def on_privmsg(self, message : BotMessage):
    color = self._chatter_color(message.author)
    text = ConsoleTextBuilder().reset().text(self._get_chatter_text(message.author)).text(": ").text(message.text)
    print(text)

  def on_chatter_join(self, event : ChatEvent):
    color = self._chatter_color(event.chatter)
    text = ConsoleTextBuilder().reset().text("[").text("+", fg=ConsoleColor.Green).reset().text("] ").text(self._get_chatter_text(event.chatter))
    print(text)

  def on_chatter_part(self, event : ChatEvent):
    color = self._chatter_color(event.chatter)
    text = ConsoleTextBuilder().reset().text("[").text("-", fg=ConsoleColor.Red).reset().text("] ").text(self._get_chatter_text(event.chatter))
    print(text)

def setup(bot : Bot):
  bot.register_plugin(UtilConsole(bot))



def teardown(bot : Bot):
  bot.unregister_plugin(UtilConsole.name)