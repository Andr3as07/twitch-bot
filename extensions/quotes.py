import io
import json
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime

import libtwitch
from libtwitch import Bot, BotMessage, Plugin
from src import pluginutil, textutil

@dataclass
class Quote:
  @classmethod
  def from_json(cls, jdata):
    result = Quote()
    result.text = jdata['text']
    result.author = jdata['author']
    result.time = jdata['timestamp']
    result.game = jdata['game']
    return result

  text : str = None
  author : str = None
  time : datetime = None # TODO
  game : str = None

class FunQuotes(Plugin):
  name = "fun.quotes"
  def __init__(self, bot):
    super().__init__(bot)
    self.config = None

  def on_load(self):
    self.config = pluginutil.load_config(self, {
      "format": "Quote #{quote.index}: {quote.text} [{quote.game}] [{quote.time}]",
      "not_found": "@{user.name}, quote not found.",
      "none_found": "@{user.name}, this channel has no quotes.",
      "out_of_range": "@{user.name}, quote must be in range 1 to {quote.count}.",
      "no_content": "@{user.name}, can not create a quote with no content.",
      "deleted": "@{user.name}, deleted quote #{quote.index}."
    })

  def _load_quotes(self, channel : libtwitch.IrcChannel) -> list[Quote]:
    dir_path = self.get_data_dir() + "/channels/" + channel.name
    self._ensure_dir(dir_path)
    path = dir_path + "/quotes.json"
    if not os.path.exists(path):
      return []

    result = []
    with open(path, 'r', encoding='utf-8') as f:
      jdata = json.load(f)
      for jquote in jdata['quotes']:
        result.append(Quote.from_json(jquote))
    return result

  def _save_quotes(self, channel : libtwitch.IrcChannel, quotes : list[Quote]):
    dir_path = self.get_data_dir() + "/channels/" + channel.name
    self._ensure_dir(dir_path)
    path = dir_path + "/quotes.json"

    quotes_list = []
    for quote in quotes:
      temp = {
        "text": quote.text,
        "author": quote.author,
        "timestamp": quote.time,
        "game": quote.game
      }
      quotes_list.append(temp)
    data = {
      "quotes": quotes_list
    }

    with open(path, 'w', encoding='utf-8') as f:
      json.dump(data, f, indent=2)
      f.flush()

  def _on_quote(self, message : BotMessage, args : list[str]):
    quotes = self._load_quotes(message.channel)

    data = {
      "user.name": message.author.login,
      "quote.count": len(quotes)
    }

    if len(quotes) == 0:
      message.response = textutil.substitute_variables(self.config['none_found'], data)
      return

    index = -1
    if len(args) >= 1:
      try:
        index = int(args[0]) - 1
      except:
        pass # ignore invalid input

    if index <= 0:
      index = -1

    if index > len(quotes) or len(quotes) == 0:
      message.response = textutil.substitute_variables(self.config['not_found'], data)
      return

    if index <= -1:
      index = random.randint(0, len(quotes) - 1)
    quote = quotes[index]

    data['quote.index'] = index + 1
    data['quote.text'] = quote.text
    data['quote.game'] = quote.game
    data['quote.time'] = quote.time
    data['quote.author'] = quote.author
    message.response = textutil.substitute_variables(self.config['format'], data)

  def _on_add_quote(self, message : BotMessage, args : list[str]):
    # TODO: Only allow moderators and the broadcaster
    quotes = self._load_quotes(message.channel)

    data = {
      "user.name": message.author.login,
      "quote.count": len(quotes)
    }

    if len(args) == 0:
      message.response = textutil.substitute_variables(self.config['no_content'], data)
      return
    new_quote = Quote()
    new_quote.text = " ".join(args)
    new_quote.author = message.author.display_name
    new_quote.time = int(time.time())
    new_quote.game = "TODO: Fetch current game"
    quotes.append(new_quote)

    self._save_quotes(message.channel, quotes)

  def _on_rem_quote(self, message : BotMessage, args : list[str]):
    # TODO: Only allow moderators and the broadcaster
    quotes = self._load_quotes(message.channel)

    data = {
      "user.name": message.author.login,
      "quote.count": len(quotes)
    }

    if len(quotes) == 0:
      message.response = textutil.substitute_variables(self.config['none_found'], data)
      return

    if len(args) == 0:
      message.response = textutil.substitute_variables(self.config['not_found'], data)
      return

    index = -1
    if len(args) >= 1:
      try:
        index = int(args[0]) - 1
      except:
        message.response = textutil.substitute_variables(self.config['not_found'], data)
        return

    if index < 0 or index >= len(quotes):
      message.response = textutil.substitute_variables(self.config['out_of_range'], data)
      return

    data['quote.index'] = index + 1
    del quotes[index]
    message.response = textutil.substitute_variables(self.config['deleted'], data)

    self._save_quotes(message.channel, quotes)

  def on_command(self, message : BotMessage, cmd : str, args : list[str]):
    if cmd == "quote":
      return self._on_quote(message, args)
    elif cmd in ["addquote", "quote+"]:
      return self._on_add_quote(message, args)
    elif cmd in ["removequote", "deletequote", "remquote", "delquote", "quote-"]:
      return self._on_rem_quote(message, args)

def setup(bot : Bot):
  bot.register_plugin(FunQuotes(bot))

def teardown(bot : Bot):
  bot.unregister_plugin("fun.quotes")