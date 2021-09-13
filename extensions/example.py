from libtwitch import Bot, Message, Plugin

class Example(Plugin):
  name = "Example"

  def on_privmsg(self, message : Message):
    print("on_privmsg", message.text)

  def on_message(self, message : Message):
    print("on_message", message.text)

def setup(bot : Bot):
  bot.register_plugin(Example(bot))

def teardown(bot : Bot):
  bot.unregister_plugin("Example")