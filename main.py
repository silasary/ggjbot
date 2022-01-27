import asyncio
import os

import aioredis
import dis_snek
import dotenv

dotenv.load_dotenv()

class Bot(dis_snek.Snake):
    def __init__(self) -> None:
        self.redis = aioredis.from_url(os.getenv('REDIS_URL', default='redis://localhost'), password=os.getenv('REDIS_PASSWORD'))
        intents = dis_snek.Intents.DEFAULT | dis_snek.Intents.GUILD_MEMBERS

        super().__init__(default_prefix='!', intents=intents, sync_interactions=True, delete_unused_application_cmds=True, fetch_members=True, role_cache={})
        super().load_extension('dis_snek.ext.debug_scale')
        super().load_extension('cogs.teamcog')
        super().load_extension('dis_taipan.updater')
        super().load_extension('dis_taipan.sentry')


    @dis_snek.listen()
    async def on_ready(self) -> None:
        print(f'{self.user} has connected to Discord!')

def init() -> None:
    client = Bot()
    client.start(os.getenv('DISCORD_TOKEN'))

if __name__ == "__main__":
    init()
