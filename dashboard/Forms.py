import discord
from modules import bot as v
from modules.models import Guild, Form
from discord.ui import DesignerView, Container, ActionRow, button, select
from dashboard._components import BackButton, FooterRow, StatusToggle, save_dash, refresh_footer

def default_form() -> Form:
    return Form(guild_id="", name="Untitled Form", description="", questions=[], settings={}, status=True)

class FormEditor(DesignerView):
    def __init__(self, guild: discord.Guild, user: discord.User, form: Form | None = None, page: str = "menu"):
        super().__init__(timeout=None)
        self.guild = guild
        self.user = user
        self.is_new = form is None
        self.form = form or Form(guild_id=str(guild.id), name="Untitled Form", description="", questions=[], settings={}, status=True)

        if page == "questions":
            self._build_questions_page()
        elif page == "settings":
            self._build_settings_page()
        else:
            self._build_menu()

    def editor(self, page: str = "menu"):
        return FormEditor(self.guild, self.user, form=self.form, page=page)

    def save_value(self, field: str, value) -> None:
        setattr(self.form, field, value)
        if not self.is_new:
            self.form.save()

    def _add_navigation(self, container: Container):
        editor = self

        class NavigationButtons(ActionRow):
            @button(label="Menu", style=discord.ButtonStyle.gray)
            async def menu(self, btn: discord.ui.Button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=editor.editor("menu"))

            @button(label="Questions", style=discord.ButtonStyle.gray)
            async def questions(self, btn: discord.ui.Button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=editor.editor("questions"))

            @button(label="Settings", style=discord.ButtonStyle.gray)
            async def settings(self, btn: discord.ui.Button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=editor.editor("settings"))

        container.add_item(NavigationButtons())

    def _build_menu(self):
        container = Container(color=discord.Color.embed_background())
        title = "Create New Form" if self.is_new else f"{self.form.name} (`{self.form.id}`)"
        container.add_text(f"## {title}")
        container.add_text(self.form.description or "*No description set.*")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
        self._add_navigation(container)
        self.add_item(container)

        editor = self

        if self.is_new:
            class CreateFormButton(ActionRow):
                @button(label="Create", style=discord.ButtonStyle.success)
                async def create(self, btn: discord.ui.Button, interaction: discord.Interaction):
                    editor.form.insert()
                    await interaction.response.send_message(
                        f"Successfully created form `{editor.form.name}`.", ephemeral=True
                    )

            self.add_item(CreateFormButton())
        else:
            self.add_item(FooterRow(self.guild, lambda: PluginForms(self.guild)))

    def _build_questions_page(self):
        container = Container(color=discord.Color.embed_background())
        container.add_text("# Questions")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
        editor = self

        if self.form.questions:
            for i, question in enumerate(self.form.questions, 1):
                container.add_text(f"**{i}.** {question.get('label', 'Untitled question')}")
        else:
            container.add_text("*No questions added yet.*")

        class AddQuestionModal(discord.ui.DesignerModal):
            def __init__(self):
                super().__init__(
                    discord.ui.Label(
                        "Question",
                        discord.ui.InputText(style=discord.InputTextStyle.short, required=True, max_length=100),
                    ),
                    title="Add Question",
                )

            async def callback(self, interaction: discord.Interaction):
                value = self.children[0].item.value
                questions = list(editor.form.questions)
                questions.append({"label": value, "type": "short"})
                editor.save_value("questions", questions)
                await interaction.response.edit_message(view=editor.editor("questions"))
                await interaction.followup.send(f"Added question: **{value}**", ephemeral=True)

        class AddQuestionButton(ActionRow):
            @button(label="Add Question", style=discord.ButtonStyle.primary, emoji="➕")
            async def callback(self, btn: discord.ui.Button, interaction: discord.Interaction):
                if self.is_new:
                    return await interaction.response.send_message(
                        "Create the form first before adding questions.", ephemeral=True
                    )
                await interaction.response.send_modal(AddQuestionModal())

        container.add_item(AddQuestionButton())
        self.add_item(container)
        self.add_item(FooterRow(self.guild, lambda: self.editor()))

    def _build_settings_page(self):
        container = Container(color=discord.Color.embed_background())
        container.add_text("# Form Settings")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
        editor = self

        class NameModal(discord.ui.DesignerModal):
            def __init__(self):
                super().__init__(
                    discord.ui.Label(
                        "Form Name",
                        discord.ui.InputText(
                            value=editor.form.name, style=discord.InputTextStyle.short, required=True, max_length=45
                        ),
                    ),
                    title="Edit Form Name",
                )

            async def callback(self, interaction: discord.Interaction):
                value = self.children[0].item.value
                editor.save_value("name", value)
                await interaction.response.edit_message(view=editor.editor("settings"))
                await interaction.followup.send(f"Updated form name to **{value}**", ephemeral=True)

        class NameButton(ActionRow):
            @button(label="Edit Name", style=discord.ButtonStyle.primary, emoji="✏️")
            async def callback(self, btn: discord.ui.Button, interaction: discord.Interaction):
                await interaction.response.send_modal(NameModal())

        container.add_text("## Name")
        container.add_item(NameButton())
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class DescriptionModal(discord.ui.DesignerModal):
            def __init__(self):
                super().__init__(
                    discord.ui.Label(
                        "Description",
                        discord.ui.InputText(
                            value=editor.form.description or "",
                            style=discord.InputTextStyle.paragraph,
                            required=False,
                            max_length=200,
                        ),
                    ),
                    title="Edit Description",
                )

            async def callback(self, interaction: discord.Interaction):
                value = self.children[0].item.value
                editor.save_value("description", value)
                await interaction.response.edit_message(view=editor.editor("settings"))
                await interaction.followup.send("Updated description.", ephemeral=True)

        class DescriptionButton(ActionRow):
            @button(label="Edit Description", style=discord.ButtonStyle.primary, emoji="📝")
            async def callback(self, btn: discord.ui.Button, interaction: discord.Interaction):
                await interaction.response.send_modal(DescriptionModal())

        container.add_text("## Description")
        container.add_item(DescriptionButton())
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        status_enabled = self.form.status

        class FormStatusToggle(ActionRow):
            @button(
                label="Enabled" if status_enabled else "Disabled",
                style=discord.ButtonStyle.green if status_enabled else discord.ButtonStyle.red,
            )
            async def callback(self, btn: discord.ui.Button, interaction: discord.Interaction):
                editor.save_value("status", btn.label == "Disabled")
                await interaction.response.edit_message(view=editor.editor("settings"))

        container.add_text("## Accepting Responses")
        container.add_item(FormStatusToggle())

        if not self.is_new:
            container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
            container.add_text("## ⚠️ Danger Zone")
            container.add_text("Deleting this form removes it and all of its questions permanently.")

            class DeleteFormButton(ActionRow):
                @button(label="Delete Form", style=discord.ButtonStyle.danger)
                async def callback(self, btn: discord.ui.Button, interaction: discord.Interaction):
                    class ConfirmDelete(discord.ui.View):
                        @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger)
                        async def confirm(self, btn: discord.ui.Button, inter: discord.Interaction):
                            editor.form.delete()
                            await inter.response.edit_message(
                                content=f"Form `{editor.form.name}` has been deleted.", view=None
                            )

                        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
                        async def cancel(self, btn: discord.ui.Button, inter: discord.Interaction):
                            await inter.response.edit_message(content="Cancelled.", view=None)

                    await interaction.response.send_message(
                        "Are you sure? This action cannot be undone.", view=ConfirmDelete(), ephemeral=True
                    )

            container.add_item(DeleteFormButton())

        self.add_item(container)
        self.add_item(FooterRow(self.guild, lambda: self.editor()))

class PluginForms(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        dash_forms = Guild.get(str(guild.id)).run().dashboard.forms

        container = Container(color=discord.Color.embed_background())
        container.add_text("# Forms")
        container.add_text("Configure forms in the dashboard.")
        container.add_item(StatusToggle(guild, "forms.status", dash_forms.get("status", False)))
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class CreateFormButton(ActionRow):
            @button(label="New Form", style=discord.ButtonStyle.primary)
            async def callback(self, btn: discord.ui.Button, interaction: discord.Interaction):
                await interaction.response.send_message(
                    view=FormEditor(guild, interaction.user), ephemeral=True
                )

        container.add_item(CreateFormButton())

        forms = Form.find(Form.guild_id == str(guild.id)).run()

        if forms:
            container.add_separator(divider=False, spacing=discord.SeparatorSpacingSize.small)
            container.add_text("## Your Forms")

            class FormSelect(ActionRow):
                @select(
                    placeholder="Select a form",
                    options=[discord.SelectOption(label=form.name, value=str(form.id)) for form in forms],
                )
                async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                    selected = next((f for f in forms if str(f.id) == select.values[0]), None)
                    if selected is None:
                        return await interaction.response.send_message("That form no longer exists.", ephemeral=True)
                    await interaction.response.edit_message(
                        view=FormEditor(guild, interaction.user, form=selected)
                    )

            container.add_item(FormSelect())
        else:
            container.add_text("*No forms created yet.*")

        self.add_item(container)