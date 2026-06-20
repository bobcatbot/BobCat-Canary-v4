import discord
from discord.ext import commands
from modules import bot as v
from discord.ui import (
    DesignerView, Container, ActionRow, select
)

BUTTON_STYLES = {
    "gray": discord.ButtonStyle.gray,
    "blurple": discord.ButtonStyle.blurple,
    "green": discord.ButtonStyle.green,
    "red": discord.ButtonStyle.red
}

# Bot Settings
from dashboard.BotSettings import PluginBotSettings

# Welcome & Goodbye
from dashboard.WelcomeGoodbye import PluginWelcomeGoodbye

# Moderation
from dashboard.Moderation import PluginModeration

# Verification
from dashboard.Verification import PluginVerification

# Forms
from dashboard.Forms import PluginForms

# Temporary Channels
from dashboard.TempChannels import PluginTempChannels

# Leveling
from dashboard.Leveling import PluginLeveling

# Birthdays
from dashboard.Birthdays import PluginBirthdays

# Economy
from dashboard.Economy import PluginEconomy

PLUGIN_OPTIONS = {
    "Bot Settings": { "plugin": PluginBotSettings,  "premium": False },
    "Welcome & Goodbye": { "plugin": PluginWelcomeGoodbye,  "premium": False },
    "Moderation": { "plugin": PluginModeration,  "premium": False },
    "Verification": { "plugin": PluginVerification,  "premium": False },
    # "Starboard": {"plugin": PluginStarboard, "premium": True},
    # "Forms": { "plugin": PluginForms,  "premium": True },
    "Temporary Channels": { "plugin": PluginTempChannels,  "premium": True },
    # "Ticketing": {"plugin": PluginTicketing, "premium": True},
    "Leveling": { "plugin": PluginLeveling,  "premium": False },
    "Birthdays": { "plugin": PluginBirthdays,  "premium": True },
    "Economy": { "plugin": PluginEconomy,  "premium": False },
}

class PluginView(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Pick a plugin")
        container.add_text("Pick a plugin to configure in the dashboard.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
        
        class PluginSelector(ActionRow):
            @select(
                placeholder="Select a plugin",
                options=[
                    discord.SelectOption(
                        label=name,
                        emoji=v.premium if plugin['premium'] and not v.db.get_server_config(guild, True)['premium']['status'] else None,
                    )
                    for name, plugin in PLUGIN_OPTIONS.items()
                ],
                custom_id="PluginSelect",
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                plugin = PLUGIN_OPTIONS.get(select.values[0])
                view_class = plugin['plugin']

                if plugin['premium'] and not v.db.get_server_config(guild, True)['premium']['status']:
                    return await interaction.response.send_message(f"{v.premium} This is a premium plugin. Please upgrade to premium to access this feature.", ephemeral=True)

                await interaction.response.send_message(view=view_class(interaction.guild))
        
        container.add_item(PluginSelector())

        self.add_item(container)

class DiscordDashboard(commands.Cog):
    def __init__(self, client):
        self.client: commands.Bot = client
    
    def author_is_mod(self, guild: discord.Guild, user: discord.Member):
        data = v.db.get_server_config(guild, True)['settings']

        if any(
            str(role.id) in data['admin_roles'] or 
            str(role.id) in data['bot_masters'] 
            for role in user.roles
        ):
            return True
        return False

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.client.guilds:
            self.client.add_view(PluginView(guild))

    @commands.slash_command(name="dashboard", description="Dashboard", guild_ids=v.guild_ids)
    @discord.option(
        name="plugin", 
        description="The plugin to configure", 
        required=False, 
        choices=list(PLUGIN_OPTIONS.keys())
    )
    async def dashboard(self, ctx: discord.ApplicationContext, plugin: str = None):
        # ADMINS AND BOT MASTERS ONLY
        mod = self.author_is_mod(ctx.guild, ctx.author)
        if not mod:
            return await ctx.respond("You do not have permission to use this command.", ephemeral=True)

        if plugin:
            plugin_data = PLUGIN_OPTIONS.get(plugin)
            view_class = plugin_data['plugin']

            if plugin_data['premium'] and not v.db.get_server_config(ctx.guild, True)['premium']['status']:
                return await ctx.respond(f"{v.premium} This is a premium plugin. Please upgrade to premium to access this feature.", ephemeral=True)

            return await ctx.respond(view=view_class(ctx.guild))
        
        # Default dashboard
        await ctx.respond(view=PluginView(ctx.guild))

def setup(client):
    client.add_cog(DiscordDashboard(client))