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

c.execute('''CREATE TABLE IF NOT EXISTS trips (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             discord_id INTEGER,
             status TEXT
          )''')

conn.commit()

current_trip_status = False

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

LOG_CHANNEL_ID = 1530791985131032656
TARGET_VERIFY_CHANNEL_ID = 1530770263598301225
VOTING_CHANNEL_ID = 1531068507050217616  
SPECIFIC_ROOM_ID = 1530770307357343895    
REQUIRED_ROLE_NAME = "GT | Trip Support"

BLACK_IMAGE_URL = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1000&auto=format&fit=crop"
CUSTOM_TRIP_IMAGE = "https://cdn.discordapp.com/attachments/1530770369060016178/1531093153854001275/IMG__.jpg?ex=6a67f51e&is=6a66a39e&hm=a1fa106680e5411b414810d4de090c586add9f6e4df1d137ec651dfe4233056b&"
CHARACTER_SYSTEM_IMAGE = "https://cdn.discordapp.com/attachments/1530770369060016178/1531093153854001275/IMG__.jpg?ex=6a67f51e&is=6a66a39e&hm=a1fa106680e5411b414810d4de090c586add9f6e4df1d137ec651dfe4233056b&"

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

def has_trip_permission(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    return any(role.name == REQUIRED_ROLE_NAME for role in member.roles)

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
            await message.add_reaction("🟡")
            guild = message.guild
            member = message.author
            
            verified_role = discord.utils.get(guild.roles, name="Verified")
            unverified_role = discord.utils.get(guild.roles, name="Unverified")
            
            if verified_role and verified_role not in member.roles:
                await member.add_roles(verified_role)
            if unverified_role and unverified_role in member.roles:
                await member.remove_roles(unverified_role)
                
            await message.channel.send(f"🟡 تم تفعيلك بنجاح يا {member.mention}! نورت السيرفر.", delete_after=5)
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

        embed_accepted = discord.Embed(title="Identity Accepted", color=discord.Color.from_str("#111111"))
        embed_accepted.description = (
            f"**Character Number |** `{char_number}`\n\n"
            f"🪪 **First Name |** `{f_name}`\n\n"
            f"🪪 **Last Name |** `{l_name}`\n\n"
            f"📅 **Birthday |** `{entered_birth}`\n\n"
            f"🪪 **Gender |** `{entered_gender}`\n\n"
            f"📍 **Birth Place |** `{entered_place}`\n\n"
            f"🪪 **ID Number |** `{new_identity}`"
        )
        embed_accepted.set_thumbnail(url=CHARACTER_SYSTEM_IMAGE)
        embed_accepted.set_image(url=CHARACTER_SYSTEM_IMAGE)
        embed_accepted.set_footer(text="© Gold Town System | 2026")

        try:
            await member.send(embed=embed_accepted)
        except Exception:
            pass

        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(content=f"🟡 **Identity Accepted:** {interaction.user.mention}", embed=embed_accepted)
            
        await interaction.followup.send(f"🟡 مبروك! اجتازت شخصيتك كافة الشروط وتم **قبولها تلقائياً** وإرسال تفاصيل الهوية إلى رسائلك الخاصة (DM).", ephemeral=True)

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

        await interaction.followup.send(f"🟡 نجحت عملية التزوير! تم تحديث هويتك واسمك إلى: `{new_full_name}`.", ephemeral=True)

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
        global current_trip_status
        if not current_trip_status:
            await interaction.response.send_message("❌ مافي رحلة الآن! لا يمكنك تسجيل الدخول للشخصية حتى تبدأ الرحلة.", ephemeral=True)
            return

        selected_identity = self.values[0]
        char_name = self.players_dict.get(selected_identity)
        member = interaction.user

        try:
            await member.edit(nick=char_name)
            await interaction.response.send_message(f"🟡 تم تسجيل الدخول بالشخصية بنجاح: `{char_name}` وتحديث نيك نيم السيرفر!", ephemeral=True)
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
            await interaction.response.send_message(f"🟡 تم تسجيل الخروج من الشخصية: `{char_name}` بنجاح.", ephemeral=True)
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
            global current_trip_status
            if not current_trip_status:
                await interaction.followup.send("❌ مافي رحلة الآن! لا يمكنك تسجيل الدخول للشخصية حتى تبدأ الرحلة.", ephemeral=True)
                return

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

class TripSetupModal(discord.ui.Modal, title='إنشاء وتثبيت لوحة الرحلة'):
    host_id = discord.ui.TextInput(label='آيدي الهوست (Host ID)', placeholder='أدخل آيدي الهوست الديسكورد...')
    co_host_id = discord.ui.TextInput(label='آيدي نائب الهوست (Co-Host ID)', placeholder='أدخل آيدي نائب الهوست...')
    trip_time = discord.ui.TextInput(label='وقت الرحلة', placeholder='مثال: 10:00 PM...')
    trip_monitors = discord.ui.TextInput(label='رقابي الرحلة (يدعم المنشن)', placeholder='اكتب أسماء أو قم بمنشن المراقبين هنا...', style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        h_id = self.host_id.value.strip()
        co_h_id = self.co_host_id.value.strip()
        t_time = self.trip_time.value.strip()
        t_monitors = self.trip_monitors.value.strip()

        embed = discord.Embed(
            title="✈️ لوحة معلومات الرحلة والتصويت",
            description=(
                f"👤 **آيدي الهوست الأساسي:**\n`{h_id}` (<@{h_id}>)\n\n"
                f"🤝 **آيدي نائب الهوست:**\n`{co_h_id}` (<@{co_h_id}>)\n\n"
                f"⏰ **وقت الرحلة:**\n`{t_time}`\n\n"
                f"🛡️ **رقابي الرحلة:**\n{t_monitors}\n\n"
                f"📜 **تعليمات هامة للرحلة:**\n"
                f"• يلتزم الجميع باحترام القوانين العامة وعدم المخالفة.\n"
                f"• يمنع منعاً باتاً التخريب أو إثارة المشاكل أثناء الرحلة.\n"
                f"• يرجى التأكد من تسجيل الدخول بالشخصية الصحيحة فور بدء الرحلة ليتمكن الجميع من رؤيتك والتصويت بدقة."
            ),
            color=discord.Color.from_str("#111111")
        )
        embed.set_image(url=CUSTOM_TRIP_IMAGE)
        
        voting_channel = bot.get_channel(VOTING_CHANNEL_ID)
        target_channel = voting_channel if voting_channel else interaction.channel

        await target_channel.send(embed=embed)

        control_view = TripControlView()
        control_msg = await target_channel.send("⚙️ **لوحة التحكم السريعة للرحلة (إعصار، تجديد، وبدء الرحلة):**", view=control_view)
        try:
            await control_msg.add_reaction("🟡")
        except Exception:
            pass

        await interaction.followup.send(f"🟡 تم نشر لوحة تحكم الرحلة والأزرار إلى روم التصويت بنجاح!", ephemeral=True)

class TripRenewModal(discord.ui.Modal, title='تجديد الرحلة وتحديث الهوست'):
    new_host_id = discord.ui.TextInput(label='آيدي الهوست الجديد (Host ID)', placeholder='أدخل آيدي الهوست الجديد...')
    new_co_host_id = discord.ui.TextInput(label='آيدي نائب الهوست الجديد (Co-Host ID)', placeholder='أدخل آيدي نائب الهوست الجديد...')

    def __init__(self, message):
        super().__init__()
        self.message = message

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        new_h_id = self.new_host_id.value.strip()
        new_co_h_id = self.new_co_host_id.value.strip()

        voting_channel = bot.get_channel(VOTING_CHANNEL_ID)
        target_channel = voting_channel if voting_channel else interaction.channel

        if voting_channel:
            async for msg in voting_channel.history(limit=10):
                if msg.embeds and "لوحة معلومات الرحلة والتصويت" in msg.embeds[0].title:
                    old_embed = msg.embeds[0]
                    updated_description = (
                        f"👤 **آيدي الهوست الأساسي:**\n`{new_h_id}` (<@{new_h_id}>)\n\n"
                        f"🤝 **آيدي نائب الهوست الجديد:**\n`{new_co_h_id}` (<@{new_co_h_id}>)\n\n"
                        f"⏰ **وقت الرحلة:**\nتم التجديد\n\n"
                        f"📜 **تعليمات هامة للرحلة:**\n"
                        f"• يلتزم الجميع باحترام القوانين العامة وعدم المخالفة.\n"
                        f"• يمنع منعاً باتاً التخريب أو إثارة المشاكل أثناء الرحلة.\n"
                        f"• يرجى التأكد من تسجيل الدخول بالشخصية الصحيحة فور بدء الرحلة ليتمكن الجميع من رؤيتك والتصويت بدقة.\n\n"
                        f"🔄 **تم تجديد الرحلة بواسطة:** {interaction.user.mention}"
                    )
                    old_embed.description = updated_description
                    old_embed.set_image(url=CUSTOM_TRIP_IMAGE)
                    await msg.edit(embed=old_embed)
                    break

        await target_channel.send(f"🔔 🔄 **تنبيه الرحلة:** تم **تجديد** الرحلة وتعيين هوست جديد (`{new_h_id}`) ونائب هوست جديد (`{new_co_h_id}`).")
        await interaction.followup.send(f"🟡 تم تجديد الرحلة وتحديث الهوست ونائب الهوست بنجاح وإرسال التنبيه إلى روم التصويت!", ephemeral=True)

class TripControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="بدء رحلة", style=discord.ButtonStyle.green, custom_id="start_trip_permanent_btn")
    async def start_trip(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_trip_permission(interaction.user):
            await interaction.response.send_message("ليس لديك الصلاحية لاستخدام هذه الأزرار.", ephemeral=True)
            return
        
        global current_trip_status
        current_trip_status = True
        
        voting_channel = bot.get_channel(VOTING_CHANNEL_ID)
        target_channel = voting_channel if voting_channel else interaction.channel

        await interaction.response.send_message("🟡 تم بدء الرحلة بنجاح وإرسال رسالة التصويت إلى روم التصويت!", ephemeral=True)
        
        poll_msg = await target_channel.send("🟢 **تنبيه الرحلة:** تم بدء الرحلة بنجاح! متاح الآن للجميع تسجيل الدخول بشخصياتهم.\n📊 **تصويت الرحلة:** هل أنت مستعد للرحلة؟ تفاعل بـ (🟡)")
        try:
            await poll_msg.add_reaction("🟡")
        except Exception:
            pass

    @discord.ui.button(label="إعصار", style=discord.ButtonStyle.red, custom_id="tornado_permanent_btn")
    async def tornado_action(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_trip_permission(interaction.user):
            await interaction.response.send_message("ليس لديك الصلاحية لاستخدام هذه الأزرار.", ephemeral=True)
            return
        
        voting_channel = bot.get_channel(VOTING_CHANNEL_ID)
        target_channel = voting_channel if voting_channel else interaction.channel

        await interaction.response.send_message("⚠️ تم إرسال تنبيه الإعصار إلى روم التصويت بنجاح.", ephemeral=True)
        await target_channel.send("🔔 ⚠️ **تنبيه طارئ:** حالة **إعصار** للرحلة الحالية! يرجى توخي الحذر.")

    @discord.ui.button(label="تجديد", style=discord.ButtonStyle.blurple, custom_id="renew_permanent_btn")
    async def renew_action(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_trip_permission(interaction.user):
            await interaction.response.send_message("ليس لديك الصلاحية لاستخدام هذه الأزرار.", ephemeral=True)
            return
        
        await interaction.response.send_modal(TripRenewModal(interaction.message))

class TripSetupSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="إدخال بيانات الرحلة", description="اضغط هنا لفتح استمارة إدخال بيانات الرحلة وإنشاء اللوحة", emoji="✈️", value="setup_trip")
        ]
        super().__init__(placeholder="اضغط هنا لإدخال بيانات الرحلة...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if not has_trip_permission(interaction.user):
            await interaction.response.send_message("ليس لديك صلاحية.", ephemeral=True)
            return
        await interaction.response.send_modal(TripSetupModal())

class TripSetupView(discord.ui.View):
    def __init__(self, timeout=None):
        super().__init__(timeout=timeout)
        self.add_item(TripSetupSelect())

@bot.command(name="trip")
async def trip_command(ctx):
    if not has_trip_permission(ctx.author):
        await ctx.send("عذراً، لا تمتلك رتبة `GT | Trip Support` أو صلاحية الأدمن لاستخدام هذا الأمر.", delete_after=5)
        return

    try:
        await ctx.message.delete()
    except Exception:
        pass
    
    view = TripSetupView()
    await ctx.send("✈️ لإنشاء لوحة التحكم الخاصة بالرحلة، اختر من القائمة أدناه:", view=view, delete_after=30)

@bot.command(name="character")
async def character_command(ctx):
    try:
        await ctx.message.delete()
    except Exception:
        pass
        
    embed = discord.Embed(title="Character Management", description="Character Creation, Login & Logout System", color=discord.Color.from_str("#111111"))
    embed.set_image(url=CHARACTER_SYSTEM_IMAGE)
    
    view = CharacterView()
    view.add_item(CharacterSelect())
    
    await ctx.send(embed=embed, view=view)

@bot.command(name="forge")
async def forge_command(ctx):
    try:
        await ctx.message.delete()
    except Exception:
        pass

    user_id = ctx.author.id
    c.execute("SELECT identity_id, first_name, last_name FROM players WHERE discord_id = ?", (user_id,))
    players = c.fetchall()
    if players:
        embed_forge = discord.Embed(title="Forgery System", description="اختر الشخصية التي تريد تزويرها من القائمة أدناه:", color=discord.Color.from_str("#111111"))
        embed_forge.set_image(url=CHARACTER_SYSTEM_IMAGE)
        await ctx.send(embed=embed_forge, view=ForgeSelectView(players))
    else:
        await ctx.send("❌ ليس لديك أي شخصيات مسجلة لتزويرها!", delete_after=5)

@bot.command(name="امسح")
async def clear_messages(ctx, amount: int = 10):
    if ctx.author != ctx.guild.owner and not ctx.author.guild_permissions.administrator:
        return
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🟡 تم حذف {amount} رسالة بنجاح.")
    await asyncio.sleep(3)
    try:
        await msg.delete()
    except:
        pass

bot.run(os.getenv('TOKEN'))
 
