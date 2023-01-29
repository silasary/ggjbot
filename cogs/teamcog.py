from naff import MISSING
import traceback
from typing import Optional

import naff
from naff import (Context, OptionTypes, check, context_menu,
                      guild_only, listen, prefixed_command, slash_command,
                      slash_option, checks)
from naff.api.events import MessageReactionAdd, MessageReactionRemove
from naff.client.errors import CommandException
from naff.client.utils import misc_utils
from naff.models import (AllowedMentions, CommandTypes, Guild, GuildText, Embed,
                             InteractionContext, Member, PrefixedContext,
                             OverwriteTypes, PermissionOverwrite, Permissions,
                             Role, GuildCategory)


class TeamBot(naff.Extension):
    def __init__(self, bot: naff.Extension) -> None:
        self.redis = bot.redis

    ### Commands

    @slash_command('team')
    async def team(ctx: Context) -> None:
        """
        Commands for managing your team.
        """
        ...

    @team.subcommand('create')
    @check(guild_only())
    @slash_option('name', 'The name of the team you want to create', OptionTypes.STRING, required=True)
    async def createteam(self, ctx: InteractionContext, name: str) -> None:
        """
        Create a new team.
        """
        await ctx.defer(False)
        team = await self.get_team(ctx.author, ctx.guild)
        if team is not None:
            raise CommandException('You already have a team')
        guild: Guild = ctx.guild
        user: Member = ctx.author
        rolename = f'Team {name}'
        if misc_utils.find(lambda r: r.name.casefold() == rolename.casefold(), guild.roles) is not None:
            raise CommandException(f'A team called "{rolename}" already exists.  Either ask someone to add you, or choose a more unique name.')
        uid = user.id
        role: Role = await guild.create_role(name=rolename, mentionable=True, reason=f'Created by {user.display_name}', permissions=Permissions(0))
        await user.add_role(role)
        await self.redis.set(f'teambot:user:{uid}', role.id)

        overwrites = [
            PermissionOverwrite(id=guild.id, type=OverwriteTypes.ROLE, deny=Permissions.VIEW_CHANNEL),  # @everyone
            PermissionOverwrite(id=role.id, type=OverwriteTypes.ROLE, allow=Permissions.VIEW_CHANNEL),  # @role
        ]

        cat = await guild.create_category(rolename, permission_overwrites=overwrites, position=MISSING)
        text: GuildText = await guild.create_text_channel('team-chat', category=cat)
        await guild.create_voice_channel('Voice', category=cat)
        await ctx.send(f'Created {text.mention} for {role.mention}', allowed_mentions=AllowedMentions.none())
        teamless = misc_utils.find(lambda r: r.name == 'Teamless', guild.roles)
        if teamless:
            await user.remove_role(teamless)


    @team.subcommand('addmember')
    @slash_option('person', 'Who are you adding?', OptionTypes.USER, required=True)
    async def addmember (self, ctx: Context, *, person: Member) -> None:
        """
        Add a member to your team.
        """
        if not ctx.guild:
            raise CommandException("This command doesn't work in DMs")

        await self.addtoteam(ctx, person)

    @context_menu(name="Add to team", context_type=CommandTypes.USER)
    async def addmember_menu(self, ctx: InteractionContext) -> None:
        """
        Add a member to your team.
        """
        if not ctx.guild:
            raise CommandException("This command doesn't work in DMs")
        member = await ctx.guild.fetch_member(ctx.target_id)
        await self.addtoteam(ctx, member)

    async def addtoteam(self, ctx, person):
        team = await self.get_team(ctx.author, ctx.guild)
        if team is None:
            raise CommandException("You don't have a team.  Make one with `/team create`")

        await person.add_role(team)
        await ctx.send(f'Added {person.mention} to {team.mention}', allowed_mentions=AllowedMentions(users=[person], roles=[]))
        if await self.get_team(person, ctx.guild) is None:
            await self.redis.set(f'teambot:user:{person.id}', team.id)
        teamless = misc_utils.find(lambda r: r.name == 'Teamless', ctx.guild.roles)
        if teamless:
            await person.remove_role(teamless)

    @team.subcommand('rename')
    @slash_option('name', 'The new name of your team', OptionTypes.STRING, required=True)
    async def renameteam (self, ctx: InteractionContext, *, name: str) -> None:
        """
        Rename your team.
        """
        if not ctx.guild:
            raise CommandException("This command doesn't work in DMs")
        team = await self.get_team(ctx.author, ctx.guild)
        if team is None:
            raise CommandException("You don't have a team.  Make one with `/team create`")

        oldname = team.name
        guild: Guild = ctx.guild
        cat = misc_utils.find(lambda c: c.name == team.name, guild.channels)
        await cat.edit(name= f'Team {name}')
        await team.edit(name=f'Team {name}')
        await ctx.send(f'{oldname} was renamed to Team {name}')

    # @team.subcommand('ping')
    # async def fixping(self, ctx: Context) -> None:
    #     if not ctx.guild:
    #         raise CommandException("This command doesn't work in DMs")

    #     team = await self.get_team(ctx.author, ctx.guild)
    #     if team is None:
    #         raise CommandException("You don't have a team.  Make one with `/team create`")
    #     await team.edit(mentionable=True)
    #     await ctx.send(f'{team.mention} can be tagged now')

    # @team.subcommand('leave')
    async def leaveteam(self, ctx: InteractionContext) -> None:
        """
        Leave your team.
        """
        if not ctx.guild:
            raise CommandException("This command doesn't work in DMs")

        team = await self.get_team(ctx.author, ctx.guild)
        if team is None:
            raise CommandException("You don't have a team.  Make one with `/team create`")

        await ctx.author.remove_roles(team)
        await ctx.send(f'You are no longer in {team.mention}', allowed_mentions=AllowedMentions.none())
        await self.redis.delete(f'teambot:user:{ctx.author.id}')

    # @team.subcommand('delete')
    async def deleteteam (self, ctx: InteractionContext) -> None:
        """
        Delete your team.  WARNING: This cannot be undone.
        """
        if not ctx.guild:
            raise CommandException("This command doesn't work in DMs")
        await ctx.defer(True)
        team = await self.get_team(ctx.author, ctx.guild)
        if team is None:
            raise CommandException("You don't have a team.  Make one with `/team create`")

        await self._delete_team(ctx, team)

    @prefixed_command('channelcount')
    async def channelcount (self, ctx: Context) -> None:
        if not ctx.guild:
            raise CommandException("This command doesn't work in DMs")
        guild: Guild = ctx.guild
        await ctx.send(f'The server is currently at {len(guild.channels)} channels')

    @check(checks.is_owner())
    @prefixed_command('flush_teams')
    async def flush(self, ctx: PrefixedContext) -> None:
        if not ctx.guild:
            raise CommandException("This command doesn't work in DMs")
        n = 0
        teams = {}
        for role in ctx.guild.roles:
            if role.name.startswith('Team '):
                teams[role.name] = role
                n += 1
        await ctx.send(f'Found {n} teams')
        f = 0
        for role in teams.values():
            if not role.members:
                await self._delete_team(ctx, role)
                f += 1

        await ctx.send(f'Flushed {f}/{n} teams')

    async def _delete_team(self, ctx: Context, role: Role) -> None:
        deleted_cat = await self.get_deleted_category(ctx)
        await role.delete()
        await ctx.send(f'Deleted {role.name}')
        if channel := misc_utils.find(lambda c: c.name == role.name, ctx.guild.channels):
            for c in channel.channels:
                if isinstance(c, GuildText):
                    await c.edit(category=deleted_cat, name=role.name.lower().replace(' ', '-'))
                    await c.send(f'Channel deleted by {ctx.author.mention}')
                else:
                    await c.delete()
            await channel.delete()

    async def get_deleted_category(self, ctx: Context) -> GuildCategory:
        deleted_cat = misc_utils.find(lambda c: c.name == 'Deleted Teams', ctx.guild.channels)
        if deleted_cat is None:
            overwrites = [
                PermissionOverwrite(id=ctx.guild.id, type=OverwriteTypes.ROLE, deny=Permissions.VIEW_CHANNEL),  # @everyone
            ]
            deleted_cat = await ctx.guild.create_category('Deleted Teams', position=None, permission_overwrites=overwrites)
        return deleted_cat

    @prefixed_command('debug_team')
    async def debug_team(self, ctx: Context, snowflake: int) -> None:
        """
        Shows debug info about a user's team.
        """
        snowflake = int(snowflake)
        if not ctx.guild:
            raise CommandException("This command doesn't work in DMs")
        member = await ctx.guild.fetch_member(snowflake)
        embed = Embed(title=str(member))
        team = await self.get_team(member, ctx.guild)
        if team is not None:
            embed.add_field(name='Team', value=team.name)
            embed.add_field(name='Team ID', value=team.id)
            embed.add_field(name='Team Members', value=', '.join(map(lambda m: m.display_name, team.members)))
        else:
            embed.add_field(name='Team', value='None')
        rid = await self.redis.get(f'teambot:user:{member.id}')
        embed.add_field(name=f'`teambot:user:{member.id}`', value=rid)
        embed.add_field(name='User Roles', value=repr(member.roles))
        await ctx.send(embed=embed)


    ### Events
    @team.error
    @createteam.error
    @addmember.error
    @renameteam.error
    @addmember_menu.error
    async def cog_command_error(self, error, ctx: Context, *args, **kwargs) -> None:
        print(repr(error))
        traceback.print_exception(type(error), error, error.__traceback__)
        if isinstance(error, CommandException):
            await ctx.send(str(error), ephemeral=True)
        else:
            await ctx.send("There was an error processing your command")

    @listen()
    async def on_message_reaction_add(self, event: MessageReactionAdd) -> None:
        if event.emoji.name == '📌':
            channel: GuildText = await self.bot.get_channel(event.message.channel.id)
            if not channel.name == 'team-chat':
                return

            await event.message.pin()

    @listen()
    async def on_message_reaction_remove(self, event: MessageReactionRemove) -> None:
        if event.emoji.name == '📌':
            channel: GuildText = await self.bot.get_channel(event.message.channel.id)
            if not channel.name == 'team-chat':
                return

            reaction = misc_utils.find(lambda r: r.emoji.name == '📌', event.message.reactions)
            if reaction and reaction.count > 1:
                return
            # raw fires before count is updated, so this is off-by-one if it's in the cache (but not if we fetched it)
            await event.message.unpin()

    ### Internals

    async def get_team(self, user: Member, guild: Guild) -> Optional[Role]:
        rid = await self.redis.get(f'teambot:user:{user.id}')
        if rid is None:
            return await self.find_team(user)
        role = await guild.fetch_role(int(rid))
        if role is None:
            return await self.find_team(user)
        if role in user.roles:
            return role
        if frole := await self.find_team(user):
            return frole
        return role


    async def find_team(self, user: Member) -> Optional[Role]:
        for r in user.roles:
            if r.name.startswith('Team '):
                await self.redis.set(f'teambot:user:{user.id}', r.id)
                return r
        return None
