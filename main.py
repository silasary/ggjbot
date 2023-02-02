import os

import aioredis
import naff
import dotenv

dotenv.load_dotenv()

class Bot(naff.Client):
    def __init__(self) -> None:
        self.redis = aioredis.from_url(os.getenv('REDIS_URL', default='redis://localhost'), password=os.getenv('REDIS_PASSWORD'))
        intents = naff.Intents.DEFAULT | naff.Intents.GUILD_MEMBERS

        super().__init__(intents=intents, sync_interactions=True, delete_unused_application_cmds=True, fetch_members=True, role_cache={})
        super().load_extension('naff.ext.sentry', token="https://5e0134f0bc3b40589d94535dac0f0394@sentry.redpoint.games/20")
        # super().load_extension('naff.ext.debug_scale')
        super().load_extension('cogs.teamcog')
        super().load_extension('cogs.roles')
        super().load_extension('dis_taipan.updater')


    @naff.listen()
    async def on_ready(self) -> None:
        print(f'{self.user} has connected to Discord!')

def init() -> None:
    client = Bot()
    client.start(os.getenv('DISCORD_TOKEN'))

if __name__ == "__main__":
    init()
