import typing
import naff
from naff import Extension, listen, slash_command, Permissions, InteractionContext, Guild, Role
from naff.client.utils import misc_utils
from naff.api.events import MemberAdd

ROLES = {

}

def find_role(guild: Guild, name: str) -> Role | None:
    return misc_utils.find(lambda r: r.name == name, guild.roles)

class Roles(Extension):
    @listen()
    async def on_member_add(self, e: MemberAdd) -> None:
        teamless = find_role(e.guild, 'Teamless')
        if teamless:
            await e.member.add_role(teamless)


    @slash_command('rolepicker', default_member_permissions=Permissions.ADMINISTRATOR)
    async def role_picker(self, ctx: InteractionContext) -> None:

        role_menu = naff.StringSelectMenu(
            options=[
                naff.SelectOption(
                    label=name,
                    # if it were up to me, the value would be the role id
                    # sadly, we must keep backwards compat
                    value=name,
                    emoji=naff.PartialEmoji(
                        id=None,
                        name=role["emoji"],
                        animated=False,
                    ),
                )
                for name, role in ROLES.items()
            ],
            placeholder="Choose a language.",
            custom_id="roles",
            min_values=1,
            max_values=len(ROLES),
        )

        await info_channel.send(components=role_menu)  # type: ignore
        await ctx.send(":white_check_mark:", ephemeral=True)


    @naff.component_callback("language_role")  # type: ignore
    async def on_astro_language_role_select(self, ctx: naff.ComponentContext):
        await ctx.defer(ephemeral=True)

        if typing.TYPE_CHECKING:
            assert isinstance(ctx.author, naff.Member)

        # same idea as subscribe, but...
        author_roles = set(ctx.author._role_ids)

        # since there are a lot more languages than roles, i wanted to make the result
        # message a bit nicer. that requires having both of these lists
        added = []
        removed = []

        for language in ctx.values:
            # language: str

            role = ROLES.get(language)
            if not role:
                # this shouldn't happen
                raise Exception('Invalid role selection')
                # return await utils.error_send(
                #     ctx, ":x: The role you selected was invalid.", naff.MaterialColors.RED
                # )

            rid = role["id"]
            if ctx.author.has_role(rid):
                author_roles.remove(rid)
                removed.append(f"`{language}`")  # thankfully, the language here is its role name
            else:
                author_roles.add(rid)
                added.append(f"`{language}`")

        await ctx.author.edit(roles=author_roles)

        resp = ":white_check_mark: "
        # yep, all we're doing is listing out the roles added and removed
        if added:
            resp += f"Added: {', '.join(added)}. "
        if removed:
            resp += f"Removed: {', '.join(removed)}."
        resp = resp.strip()  # not like it's needed, but still
        await ctx.send(resp, ephemeral=True)

