from typing import Optional
import discord
import traceback
from discord import utils
from discord import reaction
from discord.ext import commands
from discord.mentions import AllowedMentions

class TeamBot(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.redis = bot.redis

    ### Commands

    @commands.guild_only()
    @commands.command()
    async def createteam(self, ctx: commands.Context, *, name: str) -> None:
        team = await self.get_team(ctx.author, ctx.guild)
        if team is not None:
            raise commands.CheckFailure('You already have a team')
        guild: discord.Guild = ctx.guild
        user: discord.Member = ctx.author
        rolename = f'Team {name}'
        if utils.find(lambda r: r.name == rolename, guild.roles):
            raise commands.BadArgument(f'A team called "{rolename}" already exists.  Either ask someone to add you, or choose a more unique name.')
        uid = user.id
        role: discord.Role = await guild.create_role(name=rolename)
        await self.redis.set(f'teambot:user:{uid}', role.id)
        await user.add_roles(role)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            role: discord.PermissionOverwrite(read_messages=True)
        }
        cat = await guild.create_category(rolename, overwrites=overwrites)
        text: discord.TextChannel = await cat.create_text_channel('team-chat')
        await cat.create_voice_channel('Voice')
        await ctx.send(f'Created {text.mention} for {role.mention}', allowed_mentions=AllowedMentions.none())
        teamless = utils.find(lambda r: r.name == 'Teamless', guild.roles)
        if teamless:
            await user.remove_roles(teamless)


    @commands.guild_only()
    @commands.command()
    async def addmember (self, ctx: commands.Context, *, target: discord.Member) -> None:
        team = await self.get_team(ctx.author, ctx.guild)
        if team is None:
            raise commands.CheckFailure("You don't have a team.  Make one with !createteam")

        await target.add_roles(team)
        await ctx.send(f'Added {target.mention} to {team.mention}', allowed_mentions=AllowedMentions(everyone=False, users=True, roles=False))
        if await self.get_team(target, ctx.guild) is None:
            await self.redis.set(f'teambot:user:{target.id}', team.id)
        teamless = utils.find(lambda r: r.name == 'Teamless', ctx.guild.roles)
        if teamless:
            await target.remove_roles(teamless)

    ### Events

    async def cog_command_error(self, ctx: commands.Context, error) -> None:
        print(error)
        traceback.print_exception(type(error), error, error.__traceback__)
        if isinstance(error, commands.PrivateMessageOnly):
            await ctx.send("That command can only be used in Private Message with the bot")
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("You can't use this command in a private message")
        elif isinstance(error, commands.CheckFailure) or isinstance(error, commands.BadArgument):
            await ctx.send(error)
        elif isinstance(error, commands.CommandError):
            await ctx.send(f"Error executing command `{ctx.command.name}`: {str(error)}")
        else:
            await ctx.send("There was an error processing your command")

    @commands.Cog.listener('on_raw_reaction_remove')
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.emoji.name == '📌':
            add = payload.event_type == 'REACTION_ADD'
            channel: discord.TextChannel = self.bot.get_channel(payload.channel_id)
            if not channel.name == 'team-chat':
                return
            msg: discord.Message = utils.get(self.bot.cached_messages, id=payload.message_id) or await channel.fetch_message(payload.message_id)
            if add:
                await msg.pin()
            else:
                reaction = utils.find(lambda r: r.emoji == '📌', msg.reactions)
                if reaction and reaction.count > 1:
                    return
                # raw fires before count is updated, so this is off-by-one if it's in the cache (but not if we fetched it)
                await msg.unpin()



    ### Internals

    async def get_team(self, user: discord.Member, guild: discord.Guild) -> Optional[discord.Role]:
        rid = await self.redis.get(f'teambot:user:{user.id}')
        if rid is None:
            return None
        role = guild.get_role(int(rid))
        if role in user.roles:
            return role

def setup(bot: commands.Bot) -> None:
    bot.add_cog(TeamBot(bot))
