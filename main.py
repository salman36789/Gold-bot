import discord
from discord.ext import commands
import sqlite3
import os
import random

# إعداد قاعدة البيانات
conn = sqlite3.connect('rp_system.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                discord_id INTEGER, 
                identity_id INTEGER UNIQUE,
                name TEXT, 
                birthdate TEXT, 
                birthplace TEXT, 
                bio TEXT, 
                balance INTEGER, 
                status TEXT
            )''')
conn.commit()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

ADMIN_CHANNEL_ID = 123456789012345678 # ضع أيدي قناة الإدارة هنا
LOG_CHANNEL_ID = 876543210987654321   # ضع أيدي قناة اللوق هنا

class RejectModal(discord.ui.Modal, title='سبب الرفض'):
    reason = discord.ui.TextInput(label='السبب', style=discord.TextStyle.paragraph)
    
    def __init__(self, member_id, char_name, identity_id, original_message):
        super().__init__()
        self.member_id = member_id
        self.char_name = char_name
        self.identity_id = identity_id
        self.original_message = original_message
        
    async def on_submit(self, interaction: discord.Interaction):
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"❌ تم رفض الشخصية {self.char_name} (الهوية: {self.identity_id})\nالسبب: {self.reason.value}")
        await interaction.response.send_message("تم رفض الطلب وإرسال اللوق.", ephemeral=True)
        await self.original_message.delete()

class ApproveView(discord.ui.View):
    def __init__(self, member_id, char_name, identity_id, original_message):
        super().__init__(timeout=None)
        self.member_id = member_id
        self.char_name = char_name
        self.identity_id = identity_id
        self.original_message = original_message
        
    @discord.ui.button(label="قبول", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        c.execute("UPDATE players SET status = 'active' WHERE discord_id = ? AND identity_id = ?", (self.member_id, self.identity_id))
        conn.commit()
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"✅ تم قبول الشخصية {self.char_name} (رقم الهوية: {self.identity_id})")
        await interaction.response.send_message(f"تم قبول الشخصية {self.char_name} بنجاح!")
        self.stop()
        
    @discord.ui.button(label="رفض", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RejectModal(self.member_id, self.char_name, self.identity_id, self.original_message))

class RegistrationModal(discord.ui.Modal, title='إنشاء شخصية جديدة'):
    name = discord.ui.TextInput(label='اسم الشخصية', placeholder='أدخل اسم شخصيتك...', min_length=3)
    birthdate = discord.ui.TextInput(label='مواليد الشخصية', placeholder='مثال: 1998/05/12')
    birthplace = discord.ui.TextInput(label='مكان الولادة', placeholder='أدخل مكان الولادة...')
    bio = discord.ui.TextInput(label='فكرة الشخصية', style=discord.TextStyle.paragraph, placeholder='اكتب قصة أو فكرة شخصيتك هنا...')

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        
        # التحقق من عدد الشخصيات (الحد الأقصى 3)
        c.execute("SELECT COUNT(*) FROM players WHERE discord_id = ?", (user_id,))
        count = c.fetchone()[0]
        
        if count >= 3:
            await interaction.response.send_message("❌ عذراً، لا يمكنك إنشاء أكثر من 3 شخصيات!", ephemeral=True)
            return

        # توليد رقم هوية عشوائي يبدأ بالرقم 3 ومكون من 6 أرقام (غير مكرر)
        while True:
            new_identity = random.randint(300000, 399999)
            c.execute("SELECT 1 FROM players WHERE identity_id = ?", (new_identity,))
            if not c.fetchone():
                break

        # إدخال البيانات في قاعدة البيانات
        c.execute("INSERT INTO players (discord_id, identity_id, name, birthdate, birthplace, bio, balance, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                  (user_id, new_identity, self.name.value, self.birthdate.value, self.birthplace.value, self.bio.value, 1000, 'pending'))
        conn.commit()
        
        # إرسال الطلب للإدارة
        admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
        if admin_channel:
            msg = await admin_channel.send(
                f"طلب تسجيل شخصية جديدة من {interaction.user.mention}\n"
                f"🆔 **رقم الهوية العشوائي:** {new_identity}\n"
                f"👤 **اسم الشخصية:** {self.name.value}\n"
                f"📅 **المواليد:** {self.birthdate.value}\n"
                f"🌍 **مكان الولادة:** {self.birthplace.value}\n"
                f"📖 **فكرة الشخصية:** {self.bio.value}", 
                view=None
            )
            await msg.edit(view=ApproveView(user_id, self.name.value, new_identity, msg))
            
        await interaction.response.send_message(f"تم إرسال طلبك للإدارة! رقم هويتك هو: **{new_identity}** (بانتظار الموافقة).", ephemeral=True)

class CharacterSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Create Character", description="لإنشاء شخصية جديدة (بحد أقصى 3)"),
            discord.SelectOption(label="Character Login", description="لتسجيل الدخول في الرحلة"),
            discord.SelectOption(label="Character Logout", description="لتسجيل الخروج من القيم"),
            discord.SelectOption(label="Show identity", description="لعرض الهويات المسجلة")
        ]
        super().__init__(placeholder="Choose an action you want to make", options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "Create Character":
            await interaction.response.send_modal(RegistrationModal())
            
        elif self.values[0] == "Character Login":
            await interaction.response.send_message("تم تسجيل الدخول في الرحلة بنجاح.", ephemeral=True)
            
        elif self.values[0] == "Character Logout":
            await interaction.response.send_message("تم تسجيل الخروج من القيم.", ephemeral=True)
            
        elif self.values[0] == "Show identity":
            user_id = interaction.user.id
            c.execute("SELECT identity_id, name, birthdate, birthplace, balance, status FROM players WHERE discord_id = ?", (user_id,))
            players = c.fetchall()
            if players:
                text = "هوياتك المسجلة:\n"
                for idx, p in enumerate(players, 1):
                    text += f"\n**الشخصية {idx}:**\n- 🆔 الهوية: `{p[0]}`\n- 👤 الاسم: {p[1]}\n- 📅 المواليد: {p[2]}\n- 🌍 مكان الولادة: {p[3]}\n- 💰 الرصيد: {p[4]}\n- 📊 الحالة: {p[5]}\n"
                await interaction.response.send_message(text, ephemeral=True)
            else:
                await interaction.response.send_message("ليس لديك أي شخصيات مسجلة! قم بإنشاء شخصية أولاً.", ephemeral=True)

class CharacterView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(CharacterSelect())

@bot.command(name="character")
async def character_command(ctx):
    # رابط الصورة الجديدة التي أرسلتها
    image_url = "https://media.discordapp.com/attachments/1265738870128443505/1397734898519150654/Screenshot_20260726_012651.jpg" 
    
    embed = discord.Embed(title="Character Management", description="Character Creation", color=discord.Color.gold())
    embed.set_image(url=image_url)
    
    await ctx.send(embed=embed, view=CharacterView())

bot.run(os.getenv('TOKEN'))

