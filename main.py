import discord
import discord.ext.commands
import discord.ext.tasks
import os
import dotenv
import asyncio
import aioredis
import os

dotenv.load_dotenv()

class Bot(discord.ext.commands.Bot):
    def __init__(self) -> None:
        self.redis = asyncio.get_event_loop().run_until_complete(asyncio.ensure_future(aioredis.create_redis_pool(os.getenv('REDIS_URL', default='redis://localhost'), password=os.getenv('REDIS_PASSWORD'))))
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix=discord.ext.commands.when_mentioned_or('!'), intents=intents)
        super().load_extension('discordbot.owner')
        # super().load_extension('discordbot.updater')
        super().load_extension('jishaku')
        super().load_extension('cogs.teamcog')


    async def on_ready(self) -> None:
        print('Logged in as {username} ({id})'.format(username=self.user.name, id=self.user.id))
        print('Connected to {0}'.format(', '.join([server.name for server in self.guilds])))
        print('--------')

def init() -> None:
    client = Bot()
    client.run(os.getenv('DISCORD_TOKEN'))

if __name__ == "__main__":
    init()
