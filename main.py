import discord
from discord.ext import commands
import sqlite3
import os
import random
import asyncio
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, 'bot_database.db')

conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                discord_id INTEGER, 
                identity_id INTEGER UNIQUE,
                first_name TEXT,
                last_name TEXT,
                birthdate TEXT, 
                gender TEXT,
                birthplace TEXT, 
                bio TEXT, 
                balance INTEGER, 
                status TEXT
            )''')
conn.commit()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

LOG_CHANNEL_ID = 1530791985131032656
TARGET_VERIFY_CHANNEL_ID = 1530770263598301225

# الرومات المطلوبة للرحلات والإعصار والتجديد
TRIPS_CHANNEL_ID = 1530770307357343895       # روم الرحلات
NOTIFICATIONS_CHANNEL_ID = 1530770304056557751 # روم الإعصار والتجديد

# الرتبة المسموح لها بإدارة الرحلات
REQUIRED_ROLE_NAME = "GT | Trip Support"

IMAGE_URL = "https://cdn.discordapp.com/attachments/1530770297207263305/1531042208252170411/IMG__.jpg?ex=6a67c5ab&is=6a66742b&hm=999c8191853acf2d0d419692f3cbac20a15658b2dad2fe468f5104c4f05ccd13&" 
TRIP_BANNER_URL = "https://cdn.discordapp.com/attachments/1530770297207263305/1531042208252170411/IMG__.jpg?ex=6a67c5ab&is=6a66742b&hm=999c8191853acf2d0d419692f3cbac20a15658b2dad2fe468f5104c4f05ccd13&"

def has_trip_permission(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    return any(role.name == REQUIRED_ROLE_NAME for role in member.roles)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    for guild in bot.guilds:
        await setup_server_permissions(guild)
    print("Bot is online and running successfully!")

async def setup_server_permissions(guild):
    inactive_role = discord.utils.get(guild.roles, name="Inactive")
    identity_role = discord.utils.get(guild.roles, name="GT | Identity")
    
    game_categories_names = [
        "gt | on display", "gt | theft", "collection", "gt | justice team", 
        "gt | phone", "gt | command", "gold town public", "social"
    ]
    
    for cat in guild.categories:
        cat_name_lower = cat.name.lower()
        if "game" in cat_name_lower or "أقيام" in cat_name_lower or "اقيام" in cat_name_lower:
            await cat.set_permissions(guild.default_role, send_messages=False)
            if identity_role:
                await cat.set_permissions(identity_role, send_messages=False)
        elif any(name in cat_name_lower for name in game_categories_names):
            if inactive_role:
                await cat.set_permissions(inactive_role, read_messages=False, send_messages=False)
            if identity_role:
                await cat.set_permissions(identity_role, read_messages=True, send_messages=False)

@bot.event
async def on_member_join(member):
    guild = member.guild
    unverified_role = discord.utils.get(guild.roles, name="Unverified")
    inactive_role = discord.utils.get(guild.roles, name="Inactive")
    
    try:
        if unverified_role:
            await member.add_roles(unverified_role)
        if inactive_role:
            await member.add_roles(inactive_role)
    except Exception as e:
        print(f"Error on member join: {e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.id == TARGET_VERIFY_CHANNEL_ID:
        try:
            await message.add_reaction("✅")
            guild = message.guild
            member = message.author
            
            verified_role = discord.utils.get(guild.roles, name="Verified")
            unverified_role = discord.utils.get(guild.roles, name="Unverified")
            
            if verified_role and verified_role not in member.roles:
                await member.add_roles(verified_role)
            if unverified_role and unverified_role in member.roles:
                await member.remove_roles(unverified_role)
                
            await message.channel.send(f"✅ تم تفعيلك بنجاح يا {member.mention}! نورت السيرفر.", delete_after=5)
        except Exception as e:
            print(f"Error in auto-verify: {e}")

    await bot.process_commands(message)

def validate_character_data(first_name, last_name, birthdate_str, gender, birthplace, user_id):
    if re.search(r'[\u0600-\u06FF]', first_name) or re.search(r'[\u0600-\u06FF]', last_name):
        return False, "❌ تم الرفض: ممنوع كتابة الاسم باللغة العربية (يجب أن يكون بالإنجليزية)."
    
    if ' ' in first_name.strip():
        return False, "❌ تم الرفض: الاسم الأول يحتوي على مسافات، يجب أن يكون اسماً واحداً."

    c.execute("SELECT first_name FROM players WHERE discord_id = ?", (user_id,))
    existing_first_names = [row[0].lower() for row in c.fetchall()]
    if first_name.strip().lower() in existing_first_names:
        return False, "❌ تم الرفض: لا يمكنك استخدام نفس الاسم الأول لشخصية أخرى تمتلكها!"

    date_pattern = r'^(0?[1-9]|[12][0-9]|3[01])/(0?[1-9]|1[012])/([0-9]{4})$'
    if not re.match(date_pattern, birthdate_str):
        return False, "❌ تم الرفض: صيغة تاريخ الميلاد خاطئة. يجب أن تكون بهذا الشكل: `1/1/1999`."

    try:
        parts = birthdate_str.split('/')
        day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
        birth_date = datetime(year, month, day)
    except ValueError:
        return False, "❌ تم الرفض: تاريخ الميلاد غير صالح أو غير حقيقي."

    today = datetime.now()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

    if age < 18:
        return False, f"❌ تم الرفض: عمرك ({age} سنة) أصغر من الحد المسموح به (18 سنة فما فوق)."
    if age > 60:
        return False, f"❌ تم الرفض: عمرك ({age} سنة) أكبر من الحد المسموح به (60 سنة وتحت)."

    clean_gender = gender.strip().capitalize()
    if clean_gender not in ["Male", "Female"]:
        return False, "❌ تم الرفض: الجنس غير صحيح. يجب كتابة `Male` أو `Female`."

    allowed_birthplaces = ["Pollito", "Sandy", "Los"]
    clean_birthplace = birthplace.strip().capitalize()
    if clean_birthplace not in allowed_birthplaces:
        return False, "❌ تم الرفض: مكان الولادة غير مسموح به. الأماكن المسموحة فقط هي: (Pollito, Sandy, Los)."

    return True, "تم بنجاح"

class RegistrationModal(discord.ui.Modal, title='إنشاء شخصية جديدة'):
    first_name = discord.ui.TextInput(label='الاسم الأول (إنجليزي بدون مسافات)', placeholder='مثال: Jax...')
    last_name = discord.ui.TextInput(label='الاسم الثاني / العائلة (إنجليزي مسموح مسافات)', placeholder='مثال: Al Mutairi...')
    birthdate = discord.ui.TextInput(label='مواليد الشخصية (يوم/شهر/سنة)', placeholder='مثال: 1/1/1999')
    gender = discord.ui.TextInput(label='الجنس (Male / Female)', placeholder='أدخل Male أو Female...')
    birthplace = discord.ui.TextInput(label='مكان الولادة (Pollito / Sandy / Los)', placeholder='أدخل مكان الولادة...')

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        user_id = interaction.user.id
        guild = interaction.guild
        member = interaction.user
        
        f_name = self.first_name.value.strip()
        l_name = self.last_name.value.strip()
        entered_birth = self.birthdate.value.strip()
        entered_gender = self.gender.value.strip().capitalize()
        entered_place = self.birthplace.value.strip().capitalize()

        is_valid, message_result = validate_character_data(f_name, l_name, entered_birth, entered_gender, entered_place, user_id)
        if not is_valid:
            try:
                await member.send(f"❌ **عذراً، تم رفض طلب إنشاء شخصيتك.**\n**السبب:** {message_result}")
            except Exception:
                pass
            await interaction.followup.send(message_result, ephemeral=True)
            return
        
        c.execute("SELECT COUNT(*) FROM players WHERE discord_id = ?", (user_id,))
        count = c.fetchone()[0]
        
        if count >= 3:
            error_msg = "❌ عذراً، لا يمكنك امتلاك أكثر من 3 شخصيات نشطة!"
            try:
                await member.send(f"❌ **عذراً، تم رفض طلب إنشاء شخصيتك.**\n**السبب:** {error_msg}")
            except Exception:
                pass
            await interaction.followup.send(error_msg, ephemeral=True)
            return

        while True:
            new_identity = random.randint(300000, 399999)
            c.execute("SELECT 1 FROM players WHERE identity_id = ?", (new_identity,))
            if not c.fetchone():
                break

        char_number = count + 1
        role_character_name = f"{f_name} {l_name}"

        c.execute("INSERT INTO players (discord_id, identity_id, first_name, last_name, birthdate, gender, birthplace, bio, balance, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                  (user_id, new_identity, f_name, l_name, entered_birth, entered_gender, entered_place, "مقبول تلقائياً", 1000, 'active'))
        conn.commit()
        
        try:
            try:
                await member.edit(nick=role_character_name)
            except Exception as nick_err:
                print(f"Note: Nickname error: {nick_err}")

            inactive_role = discord.utils.get(guild.roles, name="Inactive")
            identity_role = discord.utils.get(guild.roles, name="GT | Identity")
            
            if inactive_role and inactive_role in member.roles:
                await member.remove_roles(inactive_role)
            
            if identity_role and identity_role not in member.roles:
                await member.add_roles(identity_role)
            
            verified_role = discord.utils.get(guild.roles, name="Verified")
            unverified_role = discord.utils.get(guild.roles, name="Unverified")
            if verified_role:
                await member.add_roles(verified_role)
            if unverified_role and unverified_role in member.roles:
                await member.remove_roles(unverified_role)

            await setup_server_permissions(guild)

        except Exception as e:
            print(f"Error in roles/permissions: {e}")

        embed_accepted = discord.Embed(title="Identity Accepted", color=discord.Color.teal())
        embed_accepted.description = (
            f"**Character Number |** `{char_number}`\n\n"
            f"🪪 **First Name |** `{f_name}`\n\n"
            f"🪪 **Last Name |** `{l_name}`\n\n"
            f"📅 **Birthday |** `{entered_birth}`\n\n"
            f"🪪 **Gender |** `{entered_gender}`\n\n"
            f"📍 **Birth Place |** `{entered_place}`\n\n"
            f"🪪 **ID Number |** `{new_identity}`"
        )
        embed_accepted.set_thumbnail(url=IMAGE_URL)
        embed_accepted.set_image(url=IMAGE_URL)
        embed_accepted.set_footer(text="© Gold Town System | 2026")

        try:
            await member.send(embed=embed_accepted)
        except Exception:
            pass

        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(content=f"🎉 **Identity Accepted:** {interaction.user.mention}", embed=embed_accepted)
            
        await interaction.followup.send(f"✅ مبروك! اجتازت شخصيتك كافة الشروط وتم **قبولها تلقائياً** وإرسال تفاصيل الهوية إلى رسائلك الخاصة (DM).", ephemeral=True)

class ForgeModal(discord.ui.Modal, title='تزوير هوية شخصية'):
    first_name = discord.ui.TextInput(label='الاسم الأول الجديد (إنجليزي)', placeholder='مثال: Jax...')
    last_name = discord.ui.TextInput(label='الاسم الثاني الجديد (مسموح مسافات)', placeholder='مثال: Al Mutairi...')
    birthdate = discord.ui.TextInput(label='مواليد الشخصية الجديدة (يوم/شهر/سنة)', placeholder='مثال: 1/1/1999')
    gender = discord.ui.TextInput(label='الجنس (Male / Female)', placeholder='أدخل Male أو Female...')
    birthplace = discord.ui.TextInput(label='مكان الولادة (Pollito / Sandy / Los)', placeholder='أدخل مكان الولادة...')

    def __init__(self, identity_id, old_full_name):
        super().__init__()
        self.identity_id = identity_id
        self.old_full_name = old_full_name

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        user_id = interaction.user.id
        guild = interaction.guild
        member = interaction.user
        
        f_name = self.first_name.value.strip()
        l_name = self.last_name.value.strip()
        entered_birth = self.birthdate.value.strip()
        entered_gender = self.gender.value.strip().capitalize()
        entered_place = self.birthplace.value.strip().capitalize()

        is_valid, message_result = validate_character_data(f_name, l_name, entered_birth, entered_gender, entered_place, user_id)
        if not is_valid:
            try:
                await member.send(f"❌ **عذراً، فشلت عملية تزوير الهوية.**\n**السبب:** {message_result}")
            except Exception:
                pass
            await interaction.followup.send(message_result, ephemeral=True)
            return

        new_full_name = f"{f_name} {l_name}"

        c.execute("""UPDATE players 
                     SET first_name = ?, last_name = ?, birthdate = ?, gender = ?, birthplace = ? 
                     WHERE identity_id = ? AND discord_id = ?""",
                  (f_name, l_name, entered_birth, entered_gender, entered_place, self.identity_id, user_id))
        conn.commit()

        try:
            try:
                await member.edit(nick=new_full_name)
            except Exception as e:
                print(f"Nickname note: {e}")
        except Exception as e:
            print(f"Error in forge role edit: {e}")

        try:
            await member.send(f"⚠️ **تم تزوير وتحديث هويتك بنجاح!**\n🆔 رقم الهوية: `{self.identity_id}`\n👤 الاسم الجديد: `{new_full_name}`\n⚧️ الجنس: `{entered_gender}`")
        except Exception:
            pass

        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(
                f"⚠️ **تم تزوير وتحديث هوية بنجاح:** {interaction.user.mention}\n"
                f"👤 **الاسم القديم:** `{self.old_full_name}` ➡️ **الاسم المزور الجديد:** `{new_full_name}`\n"
                f"🆔 **رقم الهوية:** `{self.identity_id}`"
            )

        await interaction.followup.send(f"✅ نجحت عملية التزوير! تم تحديث هويتك واسمك إلى: `{new_full_name}`.", ephemeral=True)

class ForgeSelect(discord.ui.Select):
    def __init__(self, players):
        options = []
        for p in players:
            identity_id = p[0]
            full_name = f"{p[1]} {p[2]}"
            options.append(discord.SelectOption(label=f"هوية رقم: {identity_id}", description=f"الاسم الحالي: {full_name}", value=str(identity_id)))
        super().__init__(placeholder="اختر الشخصية التي تريد تزوير هويتها...", options=options)
        self.players_dict = {str(p[0]): f"{p[1]} {p[2]}" for p in players}

    async def callback(self, interaction: discord.Interaction):
        selected_identity = self.values[0]
        old_name = self.players_dict.get(selected_identity)
        await interaction.response.send_modal(ForgeModal(int(selected_identity), old_name))

class ForgeSelectView(discord.ui.View):
    def __init__(self, players):
        super().__init__()
        self.add_item(ForgeSelect(players))

class LoginSelect(discord.ui.Select):
    def __init__(self, players):
        options = []
        for p in players:
            identity_id = p[0]
            full_name = f"{p[1]} {p[2]}"
            options.append(discord.SelectOption(label=f"تسجيل دخول: {full_name}", description=f"رقم الهوية: {identity_id}", value=str(identity_id)))
        super().__init__(placeholder="اختر الشخصية لتسجيل الدخول بها...", options=options)
        self.players_dict = {str(p[0]): f"{p[1]} {p[2]}" for p in players}

    async def callback(self, interaction: discord.Interaction):
        selected_identity = self.values[0]
        char_name = self.players_dict.get(selected_identity)
        member = interaction.user

        try:
            await member.edit(nick=char_name)
            await interaction.response.send_message(f"✅ تم تسجيل الدخول بالشخصية بنجاح: `{char_name}` وتحديث نيك نيم السيرفر!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ حدث خطأ أثناء تسجيل الدخول: {e}", ephemeral=True)

class LoginSelectView(discord.ui.View):
    def __init__(self, players):
        super().__init__()
        self.add_item(LoginSelect(players))

class LogoutSelect(discord.ui.Select):
    def __init__(self, players):
        options = []
        for p in players:
            identity_id = p[0]
            full_name = f"{p[1]} {p[2]}"
            options.append(discord.SelectOption(label=f"تسجيل خروج: {full_name}", description=f"رقم الهوية: {identity_id}", value=str(identity_id)))
        super().__init__(placeholder="اختر الشخصية لتسجيل الخروج منها...", options=options)
        self.players_dict = {str(p[0]): f"{p[1]} {p[2]}" for p in players}

    async def callback(self, interaction: discord.Interaction):
        selected_identity = self.values[0]
        char_name = self.players_dict.get(selected_identity)
        member = interaction.user

        try:
            await member.edit(nick=None)
            await interaction.response.send_message(f"✅ تم تسجيل الخروج من الشخصية: `{char_name}` بنجاح.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ حدث خطأ أثناء تسجيل الخروج: {e}", ephemeral=True)

class LogoutSelectView(discord.ui.View):
    def __init__(self, players):
        super().__init__()
        self.add_item(LogoutSelect(players))

class CharacterSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Create Character", description="إنشاء شخصية جديدة بالشروط التلقائية"),
            discord.SelectOption(label="Login", description="تسجيل الدخول بشخصية مسجلة"),
            discord.SelectOption(label="Logout", description="تسجيل الخروج من شخصية نشطة"),
            discord.SelectOption(label="Show identity", description="عرض الشخصيات والهويات المسجلة")
        ]
        super().__init__(placeholder="Choose an action you want to make", options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        
        if self.values[0] == "Create Character":
            await interaction.response.send_modal(RegistrationModal())
            return

        await interaction.response.defer(ephemeral=True)

        if self.values[0] == "Login":
            c.execute("SELECT identity_id, first_name, last_name FROM players WHERE discord_id = ?", (user_id,))
            players = c.fetchall()
            if players:
                await interaction.followup.send("اختر الشخصية لتسجيل الدخول:", view=LoginSelectView(players), ephemeral=True)
            else:
                await interaction.followup.send("❌ ليس لديك أي شخصيات مسجلة لتسجيل الدخول بها!", ephemeral=True)
        elif self.values[0] == "Logout":
            c.execute("SELECT identity_id, first_name, last_name FROM players WHERE discord_id = ?", (user_id,))
            players = c.fetchall()
            if players:
                await interaction.followup.send("اختر الشخصية لتسجيل الخروج منها:", view=LogoutSelectView(players), ephemeral=True)
            else:
                await interaction.followup.send("❌ ليس لديك شخصيات مسجلة!", ephemeral=True)
        elif self.values[0] == "Show identity":
            c.execute("SELECT identity_id, first_name, last_name, birthdate, gender, birthplace, balance FROM players WHERE discord_id = ?", (user_id,))
            players = c.fetchall()
            if players:
                text = "هوياتك المسجلة:\n"
                for idx, p in enumerate(players, 1):
                    text += f"\n**الشخصية {idx}:**\n- 👤 الاسم: `{p[1]} {p[2]}`\n- 🆔 رقم الهوية: `{p[0]}`\n- 📅 المواليد: `{p[3]}`\n- ⚧️ الجنس: `{p[4]}`\n- 📍 مكان الولادة: `{p[5]}`\n- 💰 الرصيد: `{p[6]}`\n"
                await interaction.followup.send(text, ephemeral=True)
            else:
                await interaction.followup.send("❌ ليس لديك أي شخصيات مسجلة!", ephemeral=True)

class CharacterView(discord.ui.View):
    def __init__(self, timeout=None):
        super().__init__(timeout=timeout)


# ==========================================
# ✈️ قسم أوامر وإشعارات الرحلات والأزرار
# ==========================================

class TripSetupModal(discord.ui.Modal, title='إعداد ونشر رحلة جديدة'):
    host_name = discord.ui.TextInput(label='هوست الرحلة', placeholder='أدخل اسم أو منشن الهوست...')
    assistant_name = discord.ui.TextInput(label='نائب الرحلة', placeholder='أدخل اسم أو منشن نائب الهوست...', default='لا يوجد')
    game_time = discord.ui.TextInput(label='وقت بدء الرحلة', placeholder='مثال: +15 أو الساعة 10...', default='+15')
    instructions = discord.ui.TextInput(label='تعليمات هامة', placeholder='أدخل التعليمات...', style=discord.TextStyle.paragraph, default='يرجى إضافة الهوست\nيرجى مراجعة القوانين')
    observers = discord.ui.TextInput(label='رقابي الرحلة', placeholder='أدخل أسماء الرقابة...', default='لا يوجد')

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        trips_channel = bot.get_channel(TRIPS_CHANNEL_ID)
        if not trips_channel:
            await interaction.followup.send("❌ لم يتم العثور على روم الرحلات المخصص!", ephemeral=True)
            return

        embed = discord.Embed(title="Games Notifications", color=discord.Color.teal())
        embed.description = (
            "🚀 **- Effect King's Game .**\n\n"
            "بسم الله الرحمن الرحيم ،\n"
            "حياكم الله جميعاً لمن يود الحضور يقوم بتسجيل الدخول بشخصيته عبر قائمة الشخصيات.\n\n"
            f"🏢 **| Host :** {self.host_name.value}\nالهوست\n\n"
            f"🛫 **| Assistant Host :** {self.assistant_name.value}\nنائب الرحلة\n\n"
            f"⏱️ **| Game Time :** {self.game_time.value}\nوقت بدء الرحلة\n\n"
            f"⚠️ **| Instructions :** {self.instructions.value}\nتعليمات هامة\n\n"
            f"🛡️ **| Observers :** {self.observers.value}\nرقابي الرحلة\n\n"
            "في حال واجهتك مشكله اثناء لعبك يُرجى التوجه إلى { # 📩 | Tickets }\n\n"
            "☀️ **| ختاماً :** صل على النبي ، اللهم صلي وسلم على نبينا محمد .\n\n"
            "© Effect Kings System | 2026"
        )
        embed.set_thumbnail(url=IMAGE_URL)

        msg = await trips_channel.send(embed=embed)
        try:
            await msg.add_reaction("🟡")
        except Exception:
            pass

        await interaction.followup.send("✅ تم نشر تفاصيل وبدء الرحلة في روم الرحلات بنجاح!", ephemeral=True)


class AdminTripPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="بدء رحلة", style=discord.ButtonStyle.green, custom_id="btn_start_trip")
    async def start_trip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_trip_permission(interaction.user):
            await interaction.response.send_message("❌ ليس لديك رتبة `GT | Trip Support` لاستخدام هذا الزر!", ephemeral=True)
            return
        await interaction.response.send_modal(TripSetupModal())

    @discord.ui.button(label="إعصار", style=discord.ButtonStyle.red, custom_id="btn_hurricane")
    async def hurricane_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_trip_permission(interaction.user):
            await interaction.response.send_message("❌ ليس لديك رتبة `GT | Trip Support` لاستخدام هذا الزر!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        count_logged_out = 0
        for member in guild.members:
            if member.nick and not member.bot:
                try:
                    await member.edit(nick=None)
                    count_logged_out += 1
                except Exception:
                    pass

        notif_channel = bot.get_channel(NOTIFICATIONS_CHANNEL_ID)
        if notif_channel:
            embed = discord.Embed(title="Games Notifications", color=discord.Color.red())
            embed.description = (
                "🎛️ **| Effect King's ( Close Game )**\n\n"
                "📢 **| اشعار اعصار**\n\n"
                "🏢 **| يوجد اعصار ، نتمنى من الجميع الخروج من الرحله ، رحله كانت ممتعه و نعوضكم في الرحلات القادمه بأذن الله .**\n\n"
                "⚠️ **| تعليمات الاعصار :**\n"
                "– يُمنع التفجير او التخريب .\n"
                "– يجب عليك التلفيت فوراً بعد الاعصار .\n"
                "– في حال واجهتك مشكله افتح تكت دعم فني { # 📩 | Tickets }\n\n"
                f"🔄 *تم تنفيذ تسجيل الخروج التلقائي لجميع الأعضاء.*\n\n"
                "🤍 **| شكراً لكم .**\n\n"
                "© Effect Kings System | 2026"
            )
            embed.set_thumbnail(url=IMAGE_URL)
            await notif_channel.send(embed=embed)

        await interaction.followup.send(f"✅ تم إرسال إشعار الإعصار وخروج الأعضاء بنجاح (عدد: {count_logged_out}).", ephemeral=True)

    @discord.ui.button(label="تجديد", style=discord.ButtonStyle.blurple, custom_id="btn_renew")
    async def renew_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_trip_permission(interaction.user):
            await interaction.response.send_message("❌ ليس لديك رتبة `GT | Trip Support` لاستخدام هذا الزر!", ephemeral=True)
            return

        notif_channel = bot.get_channel(NOTIFICATIONS_CHANNEL_ID)
        if notif_channel:
            embed = discord.Embed(title="Games Notifications", color=discord.Color.blue())
            embed.description = (
                "• **إشعار تجديد رحلة**\n"
                "◦ هناك تجديد رحلة متاحة الان\n"
                "◦ الرجاء من الجميع وضع خيار Last (Location)\n"
                "◦ ثم الخروج من الرحلة والدخول على الجديدة\n"
                f"◦ ايدي الهوست ونائب الهوست | `{interaction.user.name}`"
            )
            embed.set_image(url=TRIP_BANNER_URL)
            embed.set_footer(text="© Effect Kings System | 2026")
            await notif_channel.send(embed=embed)

        await interaction.response.send_message("✅ تم إرسال إشعار التجديد بنجاح في روم الإشعارات.", ephemeral=True)


@bot.command(name="trip")
async def trip_panel(ctx):
    if not has_trip_permission(ctx.author):
        return
    try:
        await ctx.message.delete()
    except:
        pass

    embed = discord.Embed(title="لوحة تحكم إدارة الرحلات", description="استخدم الأزرار أدناه لإدارة الرحلات، الإعصار، والتجديد بكل سهولة:", color=discord.Color.gold())
    await ctx.send(embed=embed, view=AdminTripPanelView())


# ==========================================

@bot.command(name="character")
async def character_command(ctx):
    try:
        await ctx.message.delete()
    except Exception:
        pass
        
    embed = discord.Embed(title="Character Management", description="Character Creation, Login & Logout System", color=discord.Color.gold())
    embed.set_image(url=IMAGE_URL)
    
    view = CharacterView()
    view.add_item(CharacterSelect())
    await ctx.send(embed=embed, view=view)

@bot.command(name="forge")
async def forge_command(ctx):
    user_id = ctx.author.id
    c.execute("SELECT identity_id, first_name, last_name FROM players WHERE discord_id = ?", (user_id,))
    players = c.fetchall()
    if players:
        embed_forge = discord.Embed(title="Forgery System", description="اختر الشخصية التي تريد تزويرها من القائمة أدناه:", color=discord.Color.dark_red())
        embed_forge.set_image(url=IMAGE_URL)
        await ctx.send(embed=embed_forge, view=ForgeSelectView(players))
    else:
        await ctx.send("❌ ليس لديك أي شخصيات مسجلة لتزويرها!", delete_after=5)

@bot.command(name="امسح")
async def clear_messages(ctx, amount: int = 10):
    if not has_trip_permission(ctx.author):
        return
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 تم حذف {amount} رسالة بنجاح.")
    await asyncio.sleep(3)
    try:
        await msg.delete()
    except:
        pass

bot.run(os.getenv('TOKEN'))

