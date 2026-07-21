import discord
from discord.ext import commands
import sqlite3

conn = sqlite3.connect('rp_system.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS players (discord_id INTEGER PRIMARY KEY, name TEXT, balance INTEGER, status TEXT)''')
conn.commit()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

ADMIN_CHANNEL_ID = 123456789012345678
LOG_CHANNEL_ID = 876543210987654321

class RejectModal(discord.ui.Modal, title='سبب الرفض'):
    reason = discord.ui.TextInput(label='السبب', style=discord.TextStyle.paragraph)
    def __init__(self, member_id, name, original_message):
        super().__init__()
        self.member_id = member_id
        self.name = name
        self.original_message = original_message
    async def on_submit(self, interaction: discord.Interaction):
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"❌ تم رفض اللاعب {self.name} (ID: {self.member_id})\nالسبب: {self.reason.value}")
        await interaction.response.send_message("تم رفض الطلب وإرسال اللوق.", ephemeral=True)
        await self.original_message.delete()

class ApproveView(discord.ui.View):
    def __init__(self, member_id, name, original_message):
        super().__init__(timeout=None)
        self.member_id = member_id
        self.name = name
        self.original_message = original_message
    @discord.ui.button(label="قبول", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        c.execute("UPDATE players SET status = 'active' WHERE discord_id = ?", (self.member_id,))
        conn.commit()
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"✅ تم قبول اللاعب {self.name}")
        await interaction.response.send_message(f"تم قبول {self.name}!")
        self.stop()
    @discord.ui.button(label="رفض", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RejectModal(self.member_id, self.name, self.original_message))

class RegistrationModal(discord.ui.Modal, title='تسجيل شخصية جديدة'):
    name = discord.ui.TextInput(label='اسم الشخصية', placeholder='أدخل اسم شخصيتك...', min_length=3)
    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        c.execute("INSERT OR REPLACE INTO players (discord_id, name, balance, status) VALUES (?, ?, ?, ?)", (user_id, self.name.value, 1000, 'pending'))
        conn.commit()
        admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
        if admin_channel:
            msg = await admin_channel.send(f"طلب تسجيل جديد من {interaction.user.mention}\nاسم الشخصية: {self.name.value}", view=None)
            await msg.edit(view=ApproveView(user_id, self.name.value, msg))
        await interaction.response.send_message("تم إرسال طلبك للإدارة، بانتظار الموافقة.", ephemeral=True)

class PhoneView(discord.ui.View):
    @discord.ui.button(label="اتصال", style=discord.ButtonStyle.blurple)
    async def call(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("جاري الاتصال...", ephemeral=True)

class BankView(discord.ui.View):
    @discord.ui.button(label="إيداع", style=discord.ButtonStyle.green)
    async def deposit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("تم إيداع المبلغ.", ephemeral=True)

class MainSystemSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Create Character", description="لإنشاء الشخصية"),
            discord.SelectOption(label="Character Login", description="لتسجيل الدخول في الرحلة"),
            discord.SelectOption(label="Character Logout", description="لتسجيل الخروج من القيم"),
            discord.SelectOption(label="Show identity", description="لعرض الهوية المسجل دخول بها"),
            discord.SelectOption(label="الجوال", description="نظام الاتصالات"),
            discord.SelectOption(label="البنك", description="نظام الخدمات المالية"),
            discord.SelectOption(label="الرحلات", description="نظام التنقل والرحلات"),
            discord.SelectOption(label="التصنيع", description="نظام تطوير الأدوات"),
            discord.SelectOption(label="السرقات", description="نظام المهام الجانبية")
        ]
        super().__init__(placeholder="Choose an action you want to make", options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "Create Character":
            await interaction.response.send_modal(RegistrationModal())
        elif self.values[0] == "الجوال":
            await interaction.response.send_message("قائمة الجوال:", view=PhoneView(), ephemeral=True)
        elif self.values[0] == "البنك":
            await interaction.response.send_message("قائمة البنك:", view=BankView(), ephemeral=True)
        else:
            await interaction.response.send_message(f"تم اختيار: {self.values[0]}", ephemeral=True)

class MainView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(MainSystemSelect())

@bot.command()
async def menu(ctx):
    await ctx.send("Character Management\nCharacter Creation", view=MainView())

bot.run('DISCORD_TOKEN')

