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
                first_name TEXT,
                last_name TEXT, 
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

# أيدي قناة اللوق الخاصة بك
LOG_CHANNEL_ID = 1530708101077012653

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
            await log_channel.send(f"❌ تم رفض الشخصية **{self.char_name}** (رقم الهوية: `{self.identity_id}`)\nالسبب: {self.reason.value}")
        await interaction.response.send_message("تم رفض الطلب وإرسال اللوق بنجاح.", ephemeral=True)
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
            await log_channel.send(f"✅ تم قبول الشخصية **{self.char_name}** (رقم الهوية: `{self.identity_id}`) بواسطة الإدارة.")
            
        await interaction.response.send_message(f"تم قبول الشخصية {self.char_name} بنجاح!", ephemeral=True)
        self.stop()
        
    @discord.ui.button(label="رفض", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RejectModal(self.member_id, self.char_name, self.identity_id, self.original_message))

class RegistrationModal(discord.ui.Modal, title='إنشاء شخصية جديدة'):
    first_name = discord.ui.TextInput(label='الاسم الأول', placeholder='أدخل الاسم الأول...', min_length=2)
    last_name = discord.ui.TextInput(label='الاسم الثاني', placeholder='أدخل الاسم الثاني...', min_length=2)
    birthdate = discord.ui.TextInput(label='مواليد الشخصية', placeholder='مثال: 1998/05/12')
    birthplace = discord.ui.TextInput(label='مكان الولادة', placeholder='أدخل مكان الولادة...')
    bio = discord.ui.TextInput(label='فكرة الشخصية', style=discord.TextStyle.paragraph, placeholder='اكتب قصة أو فكرة شخصيتك هنا...')

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        
        c.execute("SELECT COUNT(*) FROM players WHERE discord_id = ?", (user_id,))
        count = c.fetchone()[0]
        
        if count >= 3:
            await interaction.response.send_message("❌ عذراً، لا يمكنك إنشاء أكثر من 3 شخصيات!", ephemeral=True)
            return

        while True:
            new_identity = random.randint(300000, 399999)
            c.execute("SELECT 1 FROM players WHERE identity_id = ?", (new_identity,))
            if not c.fetchone():
                break

        full_name = f"{self.first_name.value} {self.last_name.value}"

        c.execute("INSERT INTO players (discord_id, identity_id, first_name, last_name, birthdate, birthplace, bio, balance, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                  (user_id, new_identity, self.first_name.value, self.last_name.value, self.birthdate.value, self.birthplace.value, self.bio.value, 1000, 'pending'))
        conn.commit()
        
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            msg = await log_channel.send(
                f"🔔 **طلب تسجيل شخصية جديدة من:** {interaction.user.mention}\n"
                f"🆔 **رقم الهوية:** `{new_identity}`\n"
                f"👤 **الاسم الكامل:** {full_name}\n"
                f"📅 **المواليد:** {self.birthdate.value}\n"
                f"🌍 **مكان الولادة:** {self.birthplace.value}\n"
                f"📖 **الفكرة:** {self.bio.value}"
            )
            await msg.edit(view=ApproveView(user_id, full_name, new_identity, msg))
            
        await interaction.response.send_message(f"تم إرسال طلبك للإدارة! رقم هويتك هو: **{new_identity}** (بانتظار الموافقة).", ephemeral=True)

class LoginSelect(discord.ui.Select):
    def __init__(self, characters):
        options = []
        for p in characters:
            # p[0] هو identity_id و p[1] هو first_name و p[2] هو last_name
            full_n = f"{p[1]} {p[2]}"
            options.append(discord.SelectOption(label=full_n, value=str(p[0]), description=f"رقم الهوية: {p[0]}"))
        super().__init__(placeholder="اختر الشخصية لتسجيل الدخول بها...", options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_identity = int(self.values[0])
        c.execute("SELECT first_name, last_name FROM players WHERE identity_id = ?", (selected_identity,))
        char = c.fetchone()
        if char:
            full_n = f"{char[0]} {char[1]}"
            await interaction.response.send_message(f"✅ تم تسجيل الدخول بنجاح بالشخصية: **{full_n}** (هوية: `{selected_identity}`)", ephemeral=True)
        else:
            await interaction.response.send_message("❌ حدث خطأ ما، لم يتم العثور على الشخصية.", ephemeral=True)

class LoginView(discord.ui.View):
    def __init__(self, characters):
        super().__init__()
        self.add_item(LoginSelect(characters))

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
        user_id = interaction.user.id
        
        if self.values[0] == "Create Character":
            await interaction.response.send_modal(RegistrationModal())
            
        elif self.values[0] == "Character Login":
            c.execute("SELECT identity_id, first_name, last_name FROM players WHERE discord_id = ? AND status = 'active'", (user_id,))
            active_chars = c.fetchall()
            
            if active_chars:
                await interaction.response.send_message("اختر الشخصية التي تريد تسجيل الدخول بها:", view=LoginView(active_chars), ephemeral=True)
            else:
                c.execute("SELECT COUNT(*) FROM players WHERE discord_id = ?", (user_id,))
                total_chars = c.fetchone()[0]
                if total_chars > 0:
                    await interaction.response.send_message("❌ لديك شخصيات مسجلة ولكنها لم تقبَل من الإدارة بعد (بانتظار الموافقة في قناة اللوق).", ephemeral=True)
                else:
                    await interaction.response.send_message("❌ أنت لم تقم بإنشاء أي شخصية بعد! قم بالضغط على (Create Character) لإنشاء شخصيتك الأولى.", ephemeral=True)
            
        elif self.values[0] == "Character Logout":
            await interaction.response.send_message("تم تسجيل الخروج بنجاح.", ephemeral=True)
            
        elif self.values[0] == "Show identity":
            c.execute("SELECT identity_id, first_name, last_name, birthdate, birthplace, balance, status FROM players WHERE discord_id = ?", (user_id,))
            players = c.fetchall()
            if players:
                text = "هوياتك المسجلة:\n"
                for idx, p in enumerate(players, 1):
                    full_n = f"{p[1]} {p[2]}"
                    status_text = "مقبولة ✅" if p[6] == 'active' else "قيد المراجعة ⏳"
                    text += f"\n**الشخصية {idx}:**\n- 🆔 الهوية: `{p[0]}`\n- 👤 الاسم: {full_n}\n- 📅 المواليد: {p[3]}\n- 🌍 مكان الولادة: {p[4]}\n- 💰 الرصيد: {p[5]}\n- 📊 الحالة: {status_text}\n"
                await interaction.response.send_message(text, ephemeral=True)
            else:
                await interaction.response.send_message("❌ ليس لديك أي شخصيات مسجلة!", ephemeral=True)

class CharacterView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(CharacterSelect())

@bot.command(name="character")
async def character_command(ctx):
    image_url = "https://cdn.discordapp.com/attachments/1530705141710327868/1530710244332929034/Screenshot_20260726_012651.jpg"
    
    embed = discord.Embed(title="Character Management", description="Character Creation", color=discord.Color.gold())
    embed.set_image(url=image_url)
    
    await ctx.send(embed=embed, view=CharacterView())

bot.run(os.getenv('TOKEN'))

