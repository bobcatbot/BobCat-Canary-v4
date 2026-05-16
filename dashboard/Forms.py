import discord
from datetime import datetime
from modules import bot as v
from discord.ui import (
    DesignerView, Container, ActionRow, button, select, channel_select, role_select
)

class ViewForms(DesignerView):
    def __init__(self, guild: discord.Guild, idx: int):
        super().__init__(timeout=None)
        data = v.db.get_server_config(guild.id)["forms"][idx]
        
        container = Container(
            color=v.style(guild),
        )
        container.add_text(f"# {data['name']} ({data['id']})")
        container.add_text(f"{data['description']}")

        self.add_item(container)

class PluginForms(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['forms']
        
        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Forms")
        container.add_text("Configure forms in the dashboard.")

        class StatusButton(ActionRow):
            @button(
                label="Disabled" if data['status'] == False else "Enabled",
                style=discord.ButtonStyle.red if data['status'] == False else discord.ButtonStyle.green,
                custom_id="status",
            )
            async def callback(self, button, interaction: discord.Interaction):
                if button.label == "Disabled":
                    v.db.update_dash(guild, 'forms.status', True)

                    button.label = "Enabled"
                    button.style = discord.ButtonStyle.green
                else:
                    v.db.update_dash(guild, 'forms.status', False)

                    button.label = "Disabled"
                    button.style = discord.ButtonStyle.red

                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(StatusButton())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class CreateFormButton(ActionRow):
            @button(
                label="Create Form",
                style=discord.ButtonStyle.primary,
            )
            async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                await interaction.response.send_message("You selected Create Form")
        container.add_item(CreateFormButton())

        class SelectForums(ActionRow):
            @select(
                placeholder="Select a form",
                options=[
                    discord.SelectOption(label=f"{option['name']}", description=f"{option['description']}", value=f"{option['id']}") 
                    for option in v.db.get_server_config(guild.id)["forms"]
                ],
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                hub_idx = None
                for idx, form in enumerate(v.db.get_server_config(guild.id)["forms"]):
                    if form['id'] == select.values[0]:
                        hub_idx = idx

                await interaction.response.send_message(view=ViewForms(guild, hub_idx))
        container.add_item(SelectForums())

        self.add_item(container)
