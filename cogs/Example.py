from libtwitch import Cog, CogEvent

class ExampleCog(Cog):
  def __init__(self, bot):
    super().__init__()
    self.bot = bot

  @Cog.command('quote')
  def quote(self, msg, args):
    msg.channel.chat("TODO: Quote command")

  @Cog.listen(CogEvent.Command)
  def on_cmd(self, msg, cmd, args):
    print("on_cmd", msg, cmd, args)

def setup(bot):
  bot.add_cog("example", ExampleCog(bot))

def teardown(bot):
  bot.remove_cog("example")