# Импорт необходимых библиотек и настройка переменных
import disnake
from disnake.ext import commands
from disnake import TextInputStyle
from mcrcon import MCRcon

# RCON конфигурация
RCON_IP = "ркон айпи"
RCON_PORT = 25566
RCON_PASS = "пароль"

# ID константы
CATEGORY_ID = #айди категории
ANKETA_ID = #айди для канала с мейн сообщением
IGROK_ROLE_ID = #роль игрока
STAFF_ROLE_ID = #стафф роль

TOKEN = "токен бота дс"

# Инициализация бота
intents = disnake.Intents.default()
intents.members = True
intents.message_content = True  # Включаем intent для обработки контента сообщений
bot = commands.Bot(command_prefix="!", intents=intents)


class ApplicationModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="Ник",
                placeholder="Введите ваш ник",
                custom_id="nick",
                style=TextInputStyle.short,
            ),
            disnake.ui.TextInput(
                label="Возраст",
                placeholder="Введите ваш возраст",
                custom_id="age",
                style=TextInputStyle.short,
            ),
            disnake.ui.TextInput(
                label="Ознакомились ли вы с правилами?",
                placeholder="Да/Нет",
                custom_id="rules",
                style=TextInputStyle.short,
            ),
            disnake.ui.TextInput(
                label="Расскажите о себе",
                placeholder="Напишите немного о себе",
                custom_id="about",
                style=TextInputStyle.paragraph,
            ),
            disnake.ui.TextInput(
                label="Кто вас позвал на сервер?",
                placeholder="Укажите ник пригласившего",
                custom_id="invited_by",
                style=TextInputStyle.short,
            ),
        ]
        super().__init__(title="Заявка на сервер", custom_id="application_modal", components=components)

    async def callback(self, interaction: disnake.ModalInteraction):
        nick = interaction.text_values["nick"]
        age = interaction.text_values["age"]
        rules = interaction.text_values["rules"]
        about = interaction.text_values["about"]
        invited_by = interaction.text_values["invited_by"]

        guild = interaction.guild
        category = disnake.utils.get(guild.categories, id=CATEGORY_ID)

        overwrites = {
            guild.default_role: disnake.PermissionOverwrite(read_messages=False),
            interaction.author: disnake.PermissionOverwrite(read_messages=True),
            guild.get_role(STAFF_ROLE_ID): disnake.PermissionOverwrite(read_messages=True)
        }

        # Создание канала заявки
        channel = await guild.create_text_channel(
            name=f"заявка-{nick}",
            category=category,
            overwrites=overwrites
        )

        # Создание embed сообщения
        embed = disnake.Embed(title=f"Заявка от {nick}", color=disnake.Color.blue())
        embed.add_field(name="Ник", value=nick)
        embed.add_field(name="Возраст", value=age)
        embed.add_field(name="Ознакомились ли вы с правилами?", value=rules)
        embed.add_field(name="Расскажите о себе", value=about)
        embed.add_field(name="Кто вас позвал на сервер?", value=invited_by)

        # Добавление кнопок "Принять" и "Отказаться"
        view = DecisionView(interaction.author)
        await channel.send(embed=embed, view=view)

        # Уведомление пользователя о создании канала
        await interaction.response.send_message(
            f"Заявка успешно создана! Перейдите в {channel.mention} для дальнейших действий.", ephemeral=True
        )


class DecisionView(disnake.ui.View):
    def __init__(self, applicant):
        super().__init__(timeout=None)
        self.applicant = applicant

    @disnake.ui.button(label="Принять", style=disnake.ButtonStyle.success)
    async def accept_button(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        if STAFF_ROLE_ID in [role.id for role in interaction.author.roles]:
            nick = interaction.message.embeds[0].fields[0].value  # Извлекаем ник из embed
            try:
                with MCRcon(RCON_IP, RCON_PASS, RCON_PORT) as mcr:
                    response = mcr.command(f"whitelist add {nick}")
                    print(f"RCON Response: {response}")
                    await interaction.response.send_message(f"Заявка {nick} принята! Ник добавлен в whitelist.", ephemeral=True)
                await interaction.channel.delete()
            except Exception as e:
                print(f"RCON Error: {e}")
                await interaction.response.send_message(f"Ошибка при добавлении {nick} в whitelist.", ephemeral=True)

        await interaction.response.send_message("Заявка принята и игрок добавлен в whitelist.", ephemeral=True)
        await interaction.channel.delete

    @disnake.ui.button(label="Отказаться", style=disnake.ButtonStyle.red)
    async def reject_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        await interaction.response.send_message(f"{self.applicant.mention}, ваша заявка была отклонена.", ephemeral=False)
        await interaction.channel.delete(delay=600)


@bot.event
async def on_ready():
    print(f"Bot {bot.user} is ready.")

    channel = bot.get_channel(ANKETA_ID)
    if channel:
        # Удаление всех старых сообщений в канале
        async for msg in channel.history(limit=None):
            await msg.delete()

        # Отправка нового сообщения с использованием вебхука
        webhook = await channel.create_webhook(name="Application Webhook")
        await webhook.send(
            content="Для подачи заявки нажмите кнопку ниже.",
            view=ApplicationButton(),
            username="SyatovBot",
            avatar_url=bot.user.avatar.url if bot.user.avatar else None
        )

        # Удаление вебхука, чтобы он не сохранялся
        await webhook.delete()


class ApplicationButton(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(label="Написать", style=disnake.ButtonStyle.blurple)
    async def write_button(self, button: disnake.ui.Button, interaction: disnake.Interaction):
        # Проверка роли IGROK_ROLE_ID
        if IGROK_ROLE_ID in [role.id for role in interaction.author.roles]:
            await interaction.response.send_message("У вас уже есть эта роль.", ephemeral=True)
        else:
            modal = ApplicationModal()
            await interaction.response.send_modal(modal)
bot.run(TOKEN)
