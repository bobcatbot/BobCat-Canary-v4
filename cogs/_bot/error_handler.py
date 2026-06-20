import sys
import traceback
import discord
import chalk
from discord.ext import commands
from modules import bot as v

ERROR_LOG_CHANNEL_ID = 1110277292124536953

# Errors that are user mistakes, not bot bugs — don't log these
IGNORED = (
    commands.MissingPermissions,
    commands.BotMissingPermissions,
    commands.MissingRequiredArgument,
    commands.BadArgument,
    commands.CheckFailure,
    commands.CommandNotFound,
    commands.CommandOnCooldown,
)


class ErrorLogger(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Core sender ───────────────────────────────────────────────────────────
    async def send_error(self, error: Exception, title: str, context: dict = None):
        """
        - Prints full traceback to console
        - Sends summary + full traceback to ERROR_LOG_CHANNEL_ID
        - Pushes a dashboard notification to the affected guild (if known)
        """
        tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))

        # Always print full traceback to console
        print(chalk.blue(f"{'='*60}"), flush=True)
        print(chalk.white(f"ERROR: {title}"), flush=True)
        print(chalk.red(tb), flush=True)
        print(chalk.blue(f"{'='*60}"), flush=True)

        # ── Discord log channel ───────────────────────────────────────────────
        channel = self.bot.get_channel(ERROR_LOG_CHANNEL_ID)
        if not channel:
            print(f"[ErrorLogger] Could not find log channel {ERROR_LOG_CHANNEL_ID}")
        else:
            # Build context string
            ctx_lines = []
            if context:
                if context.get("guild"):
                    ctx_lines.append(f"**Guild:** {context['guild']} `{context.get('guild_id', '')}`")
                if context.get("channel"):
                    ctx_lines.append(f"**Channel:** {context['channel']} `{context.get('channel_id', '')}`")
                if context.get("user"):
                    ctx_lines.append(f"**User:** {context['user']} `{context.get('user_id', '')}`")
                if context.get("command"):
                    ctx_lines.append(f"**Command:** `{context['command']}`")

            embed = discord.Embed(
                title=f"⚠️ {title}",
                description="\n".join(ctx_lines) if ctx_lines else None,
                color=discord.Color.red()
            )
            embed.add_field(name="Error Type", value=f"`{type(error).__name__}`", inline=False)
            embed.add_field(name="Message", value=f"`{str(error)[:512]}`", inline=False)
            embed.set_footer(text="See traceback below ↓")
            await channel.send(embed=embed)

            # Split traceback into 1990-char chunks and send as code blocks
            chunks = [tb[i:i+1990] for i in range(0, len(tb), 1990)]
            for i, chunk in enumerate(chunks, 1):
                label = f"Traceback ({i}/{len(chunks)})" if len(chunks) > 1 else "Traceback"
                await channel.send(f"**{label}**\n```py\n{chunk}\n```")

        # ── Dashboard notification ────────────────────────────────────────────
        # guild_id = context.get("guild_id") if context else None
        # if guild_id:
        #     try:
        #         v.push_notification(
        #             guild=guild_id,
        #             types="error",
        #             title=title,
        #             description=f"`{type(error).__name__}`: {str(error)[:200]}",
        #             fix="Check your bot's error log channel for the full traceback."
        #         )
        #     except Exception as e:
        #         print(f"[ErrorLogger] Failed to push dashboard notification: {e}")


    # ── Listeners ─────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        error = getattr(error, "original", error)

        if isinstance(error, IGNORED):
            return

        await self.send_error(
            error=error,
            title=f"Command Error: {ctx.command}",
            context={
                "guild": ctx.guild.name if ctx.guild else "DM",
                "guild_id": ctx.guild.id if ctx.guild else None,
                "channel": f"#{ctx.channel}" if ctx.guild else "DM",
                "channel_id": ctx.channel.id,
                "user": str(ctx.author),
                "user_id": ctx.author.id,
                "command": str(ctx.command),
            }
        )

    @commands.Cog.listener()
    async def on_application_command_error(self, ctx: discord.ApplicationContext, error: Exception):
        error = getattr(error, "original", error)

        if isinstance(error, IGNORED):
            return

        await self.send_error(
            error=error,
            title=f"Slash Command Error: /{ctx.command}",
            context={
                "guild": ctx.guild.name if ctx.guild else "DM",
                "guild_id": ctx.guild.id if ctx.guild else None,
                "channel": f"#{ctx.channel.name}" if ctx.guild else "DM",
                "channel_id": ctx.channel.id,
                "user": str(ctx.author),
                "user_id": ctx.author.id,
                "command": f"/{ctx.command}",
            }
        )

    @commands.Cog.listener()
    async def on_error(self, event_method: str, *args, **kwargs):
        exc_type, error, _ = sys.exc_info()

        if error is None:
            print(f"[ErrorLogger] on_error fired for '{event_method}' but no active exception found.")
            return

        # Try to extract a guild from the first arg if it's a guild-scoped event
        guild_id = None
        if args:
            first = args[0]
            if hasattr(first, "guild_id"):
                guild_id = first.guild_id
            elif hasattr(first, "guild") and first.guild:
                guild_id = first.guild.id

        await self.send_error(
            error=error,
            title=f"Event Error: {event_method}",
            context={"guild_id": guild_id} if guild_id else None,
        )


def setup(bot):
    bot.add_cog(ErrorLogger(bot))