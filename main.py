import discord
from discord.ext import commands
import sqlite3
import os
import random

DB_FILE = 'bot_database.db'

conn = sqlite3.connect(DB_FILE, check_same_thread=False)
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
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

LOG_CHANNEL_ID = 1530708101077012653

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    for guild in bot.guilds:
        print(f"جاري فحص وتأسيس رومات Gold Town في سيرفر: {guild.name}")
        
        # هيكل الأقسام والرومات (بدون أقفل وبدون تكرار)
        structure = {
            "Gold Town | Rules": [
                ("🟥 ┃ rules", False),
                ("📜 ┃ new-rules", False),
                ("🔗 ┃ pinned", False)
            ],
            "Gold Town | Ads": [
                ("📢 ┃ announcement", False),
                ("👷 ┃ updates", False),
                ("📄 ┃ merges", False),
                ("🔍 ┃ hints", False),
                ("🔮 ┃ boosters", False),
                ("🔗 ┃ partners", False)
            ],
            "GT | Rooms": [
                ("💬 ┃ general-chat", False)
            ],
            "GT | Support": [
                ("📧 ┃ tickets", False),
                ("❗ ┃ support-chat", False)
            ],
            "GT | Submit Staff": [
                ("📢 ┃ staff-ads", False),
                ("🖥️ ┃ submit-management", False)
            ],
            "Gold Town Public": [
                ("💸 ┃ credits", False),
                ("📿 ┃ athkar", False),
                ("💭 ┃ suggestions", False),
                ("🎡 ┃ events", False)
            ],
            "Social": [
                ("🎥 ┃ tiktok", False),
                ("📺 ┃ live-now", False)
            ],
            "Gold Town Identity": [
                ("📇 ┃ character-rules", False),
                ("📇 ┃ create-character", False)
            ]
        }

        # إنشاء الأقسام والرومات فقط إذا لم تكن موجودة لمنع التكرار
        for category_name, channels in structure.items():
            category = discord.utils.get(guild.categories, name=category_name)
            if not category:
                try:
                    category = await guild.create_category(category_name)
                    print(f"تم إنشاء القسم: {category_name}")
                except Exception as e:
                    print(f"فشل إنشاء القسم {category_name}: {e}")
                    continue

            for ch_name, is_private in channels:
                existing_ch = discord.utils.get(guild.channels, name=ch_name)
                if not existing_ch:
                    try:
                        overwrites = {
                            guild.default_role: discord.PermissionOverwrite(read_messages=not is_private)
                        }
                        await guild.create_text_channel(ch_name, category=category, overwrites=overwrites)
                        print(f"تم إنشاء الروم النصي: {ch_name}")
                    except Exception as e:
                        print(f"فشل إنشاء الروم {ch_name}: {e}")

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

class AdminControlView(discord.ui.View):
    def __init__(self, member_id, char_name, identity_id, original_message):
        super().__init__(timeout=None)
        self.member_id = member_id
        self.char_name = char_name
        self.identity_id = identity_id
        self.original_message = original_message
        
    def check_admin(self, interaction: discord.Interaction):
        if interaction.user.guild_permissions.administrator:
            return True
        return False

    @discord.ui.button(label="قبول", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.check_admin(interaction):
            await interaction.response.send_message("❌ عذراً، هذه الأزرار مخصصة للإدارة فقط!", ephemeral=True)
            return

        c.execute("UPDATE players SET status = 'active' WHERE discord_id = ? AND identity_id = ?", (self.member_id, self.identity_id))
        conn.commit()
        
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"✅ تم قبول الشخصية **{self.char_name}** (رقم الهوية: `{self.identity_id}`) بواسطة الإدارة ({interaction.user.mention}).")
            
        await interaction.response.send_message(f"تم قبول الشخصية {self.char_name} بنجاح!", ephemeral=True)
        self.stop()
        
    @discord.ui.button(label="رفض", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.check_admin(interaction):
            await interaction.response.send_message("❌ عذراً، هذه الأزرار مخصصة للإدارة فقط!", ephemeral=True)
            return
        await interaction.response.send_modal(RejectModal(self.member_id, self.char_name, self.identity_id, self.original_message))

    @discord.ui.button(label="حذف الشخصية", style=discord.ButtonStyle.secondary)
    async def delete_char_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.check_admin(interaction):
            await interaction.response.send_message("❌ عذراً، هذه الأزرار مخصصة للإدارة فقط!", ephemeral=True)
            return

        c.execute("DELETE FROM players WHERE identity_id = ?", (self.identity_id,))
        conn.commit()
        
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"🗑️ تم حذف الشخصية **{self.char_name}** (رقم الهوية: `{self.identity_id}`) بواسطة الإدارة ({interaction.user.mention}).")
            
        await interaction.response.send_message(f"تم حذف الشخصية ذات الهوية (`{self.identity_id}`) بنجاح.", ephemeral=True)
        await self.original_message.delete()
        self.stop()

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
            await msg.edit(view=AdminControlView(user_id, full_name, new_identity, msg))
            
        await interaction.response.send_message(f"تم إرسال طلبك للإدارة! رقم هويتك هو: **{new_identity}** (بانتظار الموافقة).", ephemeral=True)

class LoginSelect(discord.ui.Select):
    def __init__(self, characters):
        options = [discord.SelectOption(label=f"{p[1]} {p[2]}", value=str(p[0]), description=f"رقم الهوية: {p[0]}") for p in characters]
        super().__init__(placeholder="اختر الهوية المطلوبة للتبديل...", options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_identity = int(self.values[0])
        c.execute("SELECT first_name, last_name FROM players WHERE identity_id = ?", (selected_identity,))
        char = c.fetchone()
        if char:
            await interaction.response.send_message(f"✅ تم التبديل وتفعيل الهوية بنجاح: **{char[0]} {char[1]}** (هوية: `{selected_identity}`)", ephemeral=True)
        else:
            await interaction.response.send_message("❌ لم يتم العثور على الشخصية.", ephemeral=True)

class LoginView(discord.ui.View):
    def __init__(self, characters):
        super().__init__()
        self.add_item(LoginSelect(characters))

class CharacterSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Create Character", description="لإنشاء شخصية جديدة (بحد أقصى 3)"),
            discord.SelectOption(label="Character Login", description="لتسجيل الدخول بالشخصية"),
            discord.SelectOption(label="Change Identity", description="لتغيير أو التبديل بين هوياتك المسجلة"),
            discord.SelectOption(label="Character Logout", description="لتسجيل الخروج من الشخصية الحالية"),
            discord.SelectOption(label="Show identity", description="لعرض الهويات المسجلة")
        ]
        super().__init__(placeholder="Choose an action you want to make", options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        
        if self.values[0] == "Create Character":
            await interaction.response.send_modal(RegistrationModal())
            
        elif self.values[0] in ["Character Login", "Change Identity"]:
            c.execute("SELECT identity_id, first_name, last_name FROM players WHERE discord_id = ? AND status = 'active'", (user_id,))
            active_chars = c.fetchall()
            if active_chars:
                action_word = "تسجيل الدخول" if self.values[0] == "Character Login" else "تغيير الهوية إلى"
                await interaction.response.send_message(f"اختر الشخصية المراد {action_word}:", view=LoginView(active_chars), ephemeral=True)
            else:
                await interaction.response.send_message("❌ ليس لديك شخصيات مقبولة بعد.", ephemeral=True)
                
        elif self.values[0] == "Character Logout":
            await interaction.response.send_message("✅ تم تسجيل الخروج من الشخصية الحالية بنجاح.", ephemeral=True)
            
        elif self.values[0] == "Show identity":
            c.execute("SELECT identity_id, first_name, last_name, birthdate, birthplace, balance, status FROM players WHERE discord_id = ?", (user_id,))
            players = c.fetchall()
            if players:
                text = "هوياتك المسجلة:\n"
                for idx, p in enumerate(players, 1):
                    status_text = "مقبولة ✅" if p[6] == 'active' else "قيد المراجعة ⏳"
                    text += f"\n**الشخصية {idx}:**\n- 🆔 الهوية: `{p[0]}`\n- 👤 الاسم: {p[1]} {p[2]}\n- 📅 المواليد: {p[3]}\n- 🌍 مكان الولادة: {p[4]}\n- 💰 الرصيد: {p[5]}\n- 📊 الحالة: {status_text}\n"
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

class AdminSelectChar(discord.ui.Select):
    def __init__(self, characters, action_type):
        self.action_type = action_type
        options = [discord.SelectOption(label=f"{p[1]} {p[2]} (هوية: {p[0]})", value=str(p[0])) for p in characters]
        super().__init__(placeholder="اختر الشخصية المطلوبة...", options=options)

    async def callback(self, interaction: discord.Interaction):
        identity_id = int(self.values[0])
        if self.action_type == "delete":
            c.execute("DELETE FROM players WHERE identity_id = ?", (identity_id,))
            conn.commit()
            await interaction.response.send_message(f"🗑️ تم حذف الشخصية ذات الهوية (`{identity_id}`) بنجاح.", ephemeral=True)
        elif self.action_type == "edit":
            await interaction.response.send_modal(AdminEditModal(identity_id))

class AdminCharView(discord.ui.View):
    def __init__(self, characters, action_type):
        super().__init__()
        self.add_item(AdminSelectChar(characters, action_type))

class AdminEditModal(discord.ui.Modal, title='تعديل بيانات الشخصية'):
    first_name = discord.ui.TextInput(label='الاسم الأول الجديد', placeholder='أدخل الاسم الأول...')
    last_name = discord.ui.TextInput(label='الاسم الثاني الجديد', placeholder='أدخل الاسم الثاني...')
    birthplace = discord.ui.TextInput(label='مكان الولادة الجديد', placeholder='أدخل مكان الولادة...')
    bio = discord.ui.TextInput(label='فكرة الشخصية الجديدة', style=discord.TextStyle.paragraph)

    def __init__(self, identity_id):
        super().__init__()
        self.identity_id = identity_id

    async def on_submit(self, interaction: discord.Interaction):
        c.execute("UPDATE players SET first_name = ?, last_name = ?, birthplace = ?, bio = ? WHERE identity_id = ?", 
                  (self.first_name.value, self.last_name.value, self.birthplace.value, self.bio.value, self.identity_id))
        conn.commit()
        await interaction.response.send_message(f"✅ تم تحديث بيانات الشخصية ذات الهوية (`{self.identity_id}`) بنجاح!", ephemeral=True)

@bot.command(name="deletechar")
@commands.has_permissions(administrator=True)
async def deletechar_cmd(ctx, member: discord.Member):
    c.execute("SELECT identity_id, first_name, last_name FROM players WHERE discord_id = ?", (member.id,))
    chars = c.fetchall()
    if chars:
        await ctx.send(f"اختر الشخصية التي تريد حذفها للعضو {member.mention}:", view=AdminCharView(chars, "delete"))
    else:
        await ctx.send("❌ هذا العضو ليس لديه أي شخصيات مسجلة.")

@bot.command(name="editchar")
@commands.has_permissions(administrator=True)
async def editchar_cmd(ctx, member: discord.Member):
    c.execute("SELECT identity_id, first_name, last_name FROM players WHERE discord_id = ?", (member.id,))
    chars = c.fetchall()
    if chars:
        await ctx.send(f"اختر الشخصية التي تريد تعديلها للعضو {member.mention}:", view=AdminCharView(chars, "edit"))
    else:
        await ctx.send("❌ هذا العضو ليس لديه أي شخصيات مسجلة.")

@bot.command(name="امسح")
@commands.has_permissions(administrator=True)
async def clear_messages(ctx, amount: int = 10):
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 تم حذف {amount} رسالة بنجاح.")
    await discord.utils.sleep_until(discord.utils.utcnow() + discord.utils.timedelta(seconds=3))
    try:
        await msg.delete()
    except:
        pass

bot.run(os.getenv('TOKEN'))

