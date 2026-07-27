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

# 1. جدول الشخصيات والهويات
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

# 2. جدول الرحلات
c.execute('''CREATE TABLE IF NOT EXISTS trips (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             discord_id INTEGER,
             status TEXT
          )''')

# 3. جدول الحسابات البنكية (رصيد افتراضي 5000)
c.execute('''CREATE TABLE IF NOT EXISTS bank_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                discord_id INTEGER UNIQUE,
                account_name TEXT,
                pin_code TEXT,
                iban TEXT,
                balance INTEGER DEFAULT 5000
            )''')

# 4. جدول شنطة اللاعبين والأدوات (احتياطي للأنظمة)
c.execute('''CREATE TABLE IF NOT EXISTS user_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id INTEGER,
                item_key TEXT,
                item_name TEXT,
                item_count INTEGER,
                item_image TEXT
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
TARGET_ACTION_ROOM_ID = 1530770304056557751  # روم إرسال إشعارات الإعصار والتجديد
BANK_LOG_CHANNEL_ID = 1531305086666412163  # روم سجلات البنك
REQUIRED_ROLE_NAME = "GT | Trip Support"

BLACK_IMAGE_URL = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1000&auto=format&fit=crop"
CUSTOM_TRIP_IMAGE = "https://cdn.discordapp.com/attachments/1530770369060016178/1531093153854001275/IMG__.jpg?ex=6a67f51e&is=6a66a39e&hm=a1fa106680e5411b414810d4de090c586add9f6e4df1d137ec651dfe4233056b&"
CHARACTER_SYSTEM_IMAGE = "https://cdn.discordapp.com/attachments/1530770369060016178/1531093153854001275/IMG__.jpg?ex=6a67f51e&is=6a66a39e&hm=a1fa106680e5411b414810d4de090c586add9f6e4df1d137ec651dfe4233056b&"
BANK_IMAGE_URL = "https://cdn.discordapp.com/attachments/1530770369060016178/1531093153854001275/IMG__.jpg?ex=6a67f51e&is=6a66a39e&hm=a1fa106680e5411b414810d4de090c586add9f6e4df1d137ec651dfe4233056b&"

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
        number_words = ["الاولى", "الثانية", "الثالثة"]
        for idx, p in enumerate(players):
            identity_id = p[0]
            full_name = f"{p[1]} {p[2]}"
            label = f"الشخصية {number_words[idx]}" if idx < len(number_words) else f"الشخصية {idx + 1}"
            options.append(discord.SelectOption(label=label, description=f"الاسم: {full_name} | الهوية: {identity_id}", value=str(identity_id)))
        super().__init__(placeholder="Choose a character you want to join with", options=options)
        self.players_dict = {str(p[0]): p for p in players}

    async def callback(self, interaction: discord.Interaction):
        global current_trip_status
        if not current_trip_status:
            await interaction.response.send_message("❌ مافي رحلة الآن! لا يمكنك تسجيل الدخول للشخصية حتى تبدأ الرحلة.", ephemeral=True)
            return

        selected_identity = self.values[0]
        player_data = self.players_dict.get(selected_identity)
        identity_id = player_data[0]
        f_name = player_data[1]
        l_name = player_data[2]
        birthdate = player_data[3]
        gender = player_data[4]
        birthplace = player_data[5]
        balance = player_data[6]
        
        full_name = f"{f_name} {l_name}"
        member = interaction.user

        c.execute("SELECT balance FROM bank_accounts WHERE discord_id = ?", (member.id,))
        bank_row = c.fetchone()
        bank_balance = bank_row[0] if bank_row else 5000

        try:
            await member.edit(nick=full_name)
            
            embed_login = discord.Embed(
                title="Gold Town",
                description=(
                    f"**First Name**          `{f_name}`\n"
                    f"**Birthdate**         `{birthdate}`\n"
                    f"**Gender**            `{gender}`\n"
                    f"**Nationality**     `{birthplace}`\n"
                    f"**Job**               `Police`\n"
                    f"**Cash**              `{balance} $`\n"
                    f"**Bank**              `{bank_balance} $`"
                ),
                color=discord.Color.gold()
            )
            embed_login.set_image(url=CHARACTER_SYSTEM_IMAGE)
            embed_login.set_footer(text=f"Identity Number: {identity_id}")

            await interaction.response.send_message(embed=embed_login, ephemeral=True)
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

            c.execute("SELECT identity_id, first_name, last_name, birthdate, gender, birthplace, balance FROM players WHERE discord_id = ?", (user_id,))
            players = c.fetchall()
            if players:
                await interaction.followup.send("Choose a character you want to join with", view=LoginSelectView(players), ephemeral=True)
            else:
                await interaction.followup.send("❌ ليس لديك أي شخصيات مسجلة لت تسجيل الدخول بها!", ephemeral=True)
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
        
        voting_channel = bot.get_channel(SPECIFIC_ROOM_ID)
        target_channel = voting_channel if voting_channel else interaction.channel

        poll_msg = await target_channel.send(embed=embed)
        try:
            await poll_msg.add_reaction("🟡")
        except Exception:
            pass

        await interaction.followup.send(f"🟡 تم نشر لوحة معلومات الرحلة والتصويت في روم التصويت بنجاح!", ephemeral=True)

class TripRenewModal(discord.ui.Modal, title='تجديد الرحلة وتحديث الهوست'):
    new_host_id = discord.ui.TextInput(label='آيدي الهوست الجديد (Host ID)', placeholder='أدخل آيدي الهوست الجديد...')
    new_co_host_id = discord.ui.TextInput(label='آيدي نائب الهوست الجديد (Co-Host ID)', placeholder='أدخل آيدي نائب الهوست الجديد...')

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        new_h_id = self.new_host_id.value.strip()
        new_co_h_id = self.new_co_host_id.value.strip()

        action_channel = bot.get_channel(TARGET_ACTION_ROOM_ID)
        target_channel = action_channel if action_channel else interaction.channel

        embed_renew = discord.Embed(
            title="Effect King's ( Renew Trip )",
            description=(
                f"• **إشعار تجديد رحلة**\n"
                f"  ◦ **هناك تجديد رحلة متاح الان**\n"
                f"  ◦ **الرجاء من الجميع وضع خيار Last (Location)**\n"
                f"  ◦ **ثم الخروج من الرحلة والدخول على الجديدة**\n"
                f"  ◦ **ايدي الهوست |** `{new_h_id}` (<@{new_h_id}>)\n"
                f"  ◦ **ايدي نائب الهوست |** `{new_co_h_id}` (<@{new_co_h_id}>)"
            ),
            color=discord.Color.from_str("#111111")
        )
        embed_renew.set_image(url=CUSTOM_TRIP_IMAGE)
        embed_renew.set_footer(text="© Effect Kings System | 2026")

        await target_channel.send(embed=embed_renew)
        await interaction.followup.send(f"🟡 تم إرسال إشعار تجديد الرحلة إلى الروم المحدد بنجاح!", ephemeral=True)

class TripControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="إدخال بيانات الرحلة", style=discord.ButtonStyle.secondary, emoji="✈️", custom_id="setup_trip_modal_btn", row=0)
    async def setup_trip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_trip_permission(interaction.user):
            await interaction.response.send_message("ليس لديك صلاحية.", ephemeral=True)
            return
        await interaction.response.send_modal(TripSetupModal())

    @discord.ui.button(label="بدء رحلة", style=discord.ButtonStyle.green, custom_id="start_trip_permanent_btn", row=0)
    async def start_trip(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_trip_permission(interaction.user):
            await interaction.response.send_message("ليس لديك الصلاحية لاستخدام هذه الأزرار.", ephemeral=True)
            return
        
        global current_trip_status
        current_trip_status = True
        
        await interaction.response.send_message("🟢 تم بدء الرحلة بنجاح وأصبح متاحاً للجميع تسجيل الدخول بشخصياتهم.", ephemeral=True)

    @discord.ui.button(label="إعصار", style=discord.ButtonStyle.red, custom_id="tornado_permanent_btn", row=1)
    async def tornado_action(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_trip_permission(interaction.user):
            await interaction.response.send_message("ليس لديك الصلاحية لاستخدام هذه الأزرار.", ephemeral=True)
            return
        
        action_channel = bot.get_channel(TARGET_ACTION_ROOM_ID)
        target_channel = action_channel if action_channel else interaction.channel

        embed_tornado = discord.Embed(
            title="Effect King's ( Close Game )",
            description=(
                f"📢 **| اشعار اعصار**\n\n"
                f"🏙️ **| يوجد اعصار ، نتمنى من الجميع الخروج من الرحله ، رحله كانت ممتعة و نعوضكم في الرحلات القادمه بأذن الله .**\n\n"
                f"🛑 **| تعليمات الاعصار :**\n"
                f"  — **يُمنع التفجير او التخريب .**\n"
                f"  — **يجب عليك التلفيت فوراً بعد الاعصار .**\n"
                f"  — **في حال واجهت مشكله افتح تكت دعم فني | Tickets .**\n\n"
                f"🤍 **| شكراً لكم .**"
            ),
            color=discord.Color.from_str("#111111")
        )
        embed_tornado.set_image(url=CUSTOM_TRIP_IMAGE)
        embed_tornado.set_footer(text="© Effect Kings System | 2026")

        await target_channel.send(embed=embed_tornado)
        await interaction.response.send_message("⚠️ تم إرسال تنبيه الإعصار (الإيمبد) إلى الروم المحدد بنجاح.", ephemeral=True)

    @discord.ui.button(label="تجديد", style=discord.ButtonStyle.blurple, custom_id="renew_permanent_btn", row=1)
    async def renew_action(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_trip_permission(interaction.user):
            await interaction.response.send_message("ليس لديك الصلاحية لاستخدام هذه الأزرار.", ephemeral=True)
            return
        
        await interaction.response.send_modal(TripRenewModal())

# ==================== (أنظمة البنك المتقدمة والقوائم) ====================

class DepositModal(discord.ui.Modal, title='إيداع أموال في البنك'):
    amount = discord.ui.TextInput(label='المبلغ المراد إيداعه', placeholder='أدخل المبلغ بالأرقام...')

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            deposit_amount = int(self.amount.value.strip())
            if deposit_amount <= 0:
                raise ValueError()
        except ValueError:
            await interaction.followup.send("❌ الرجاء إدخال رقم صحيح للمبلغ!", ephemeral=True)
            return

        user_id = interaction.user.id
        
        # جلب أول شخصية نشطة للاعب لمعرفة الكاش
        c.execute("SELECT id, balance FROM players WHERE discord_id = ? ORDER BY id ASC LIMIT 1", (user_id,))
        player = c.fetchone()
        
        if not player:
            await interaction.followup.send("❌ ليس لديك أي شخصية مسجلة لتسحب منها الكاش!", ephemeral=True)
            return
        
        player_db_id, player_cash = player[0], player[1]

        if deposit_amount > player_cash:
            await interaction.followup.send("❌ ماعندك أموال كافيه في الكاش!", ephemeral=True)
            return

        # خصم المبلغ من الكاش وإضافته للبنك
        c.execute("UPDATE players SET balance = balance - ? WHERE id = ?", (deposit_amount, player_db_id))
        c.execute("UPDATE bank_accounts SET balance = balance + ? WHERE discord_id = ?", (deposit_amount, user_id))
        conn.commit()

        embed = discord.Embed(
            title="📥 - Deposit Success",
            description=f"✅ تم إيداع مبلغ `{deposit_amount} $` بنجاح إلى حسابك البنكي!",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

class WithdrawModal(discord.ui.Modal, title='سحب أموال من البنك'):
    amount = discord.ui.TextInput(label='المبلغ المراد سحبه', placeholder='أدخل المبلغ بالأرقام...')

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            withdraw_amount = int(self.amount.value.strip())
            if withdraw_amount <= 0:
                raise ValueError()
        except ValueError:
            await interaction.followup.send("❌ الرجاء إدخال رقم صحيح للمبلغ!", ephemeral=True)
            return

        user_id = interaction.user.id
        
        c.execute("SELECT balance FROM bank_accounts WHERE discord_id = ?", (user_id,))
        bank_row = c.fetchone()
        if not bank_row:
            await interaction.followup.send("❌ ليس لديك حساب بنكي!", ephemeral=True)
            return
        
        bank_balance = bank_row[0]

        if withdraw_amount > bank_balance:
            await interaction.followup.send("❌ فلوسك ماتكفي الي في البنك!", ephemeral=True)
            return

        c.execute("SELECT id FROM players WHERE discord_id = ? ORDER BY id ASC LIMIT 1", (user_id,))
        player = c.fetchone()
        if not player:
            await interaction.followup.send("❌ ليس لديك شخصية لتضيف إليها الكاش المسحوب!", ephemeral=True)
            return
        
        player_db_id = player[0]

        # خصم من البنك وإضافة للكاش
        c.execute("UPDATE bank_accounts SET balance = balance - ? WHERE discord_id = ?", (withdraw_amount, user_id))
        c.execute("UPDATE players SET balance = balance + ? WHERE id = ?", (withdraw_amount, player_db_id))
        conn.commit()

        embed = discord.Embed(
            title="📤 - Withdraw Success",
            description=f"✅ تم سحب مبلغ `{withdraw_amount} $` بنجاح وإضافته إلى كاش شخصيتك!",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

class TransferModal(discord.ui.Modal, title='تحويل أموال لحساب آخر'):
    target_id = discord.ui.TextInput(label='آيبان المستلم أو رقم الهوية', placeholder='أدخل IBAN أو رقم هوية المستلم...')
    amount = discord.ui.TextInput(label='المبلغ المراد تحويله', placeholder='أدخل المبلغ بالأرقام...')

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        target_input = self.target_id.value.strip()
        try:
            transfer_amount = int(self.amount.value.strip())
            if transfer_amount <= 0:
                raise ValueError()
        except ValueError:
            await interaction.followup.send("❌ الرجاء إدخال رقم صحيح للمبلغ!", ephemeral=True)
            return

        sender_id = interaction.user.id

        # فحص رصيد المرسل في البنك
        c.execute("SELECT balance FROM bank_accounts WHERE discord_id = ?", (sender_id,))
        sender_bank = c.fetchone()
        if not sender_bank:
            await interaction.followup.send("❌ ليس لديك حساب بنكي!", ephemeral=True)
            return
        
        if transfer_amount > sender_bank[0]:
            await interaction.followup.send("❌ رصيدك في البنك لا يكفي لإتمام عملية التحويل!", ephemeral=True)
            return

        # البحث عن المستلم إما عن طريق الآيبان أو رقم الهوية
        recipient_discord_id = None
        
        # محاولة البحث كـ آيبان بنكي
        c.execute("SELECT discord_id FROM bank_accounts WHERE iban = ?", (target_input,))
        rec_acc = c.fetchone()
        if rec_acc:
            recipient_discord_id = rec_acc[0]
        else:
            # محاولة البحث برقم الهوية الشخصية
            try:
                identity_num = int(target_input)
                c.execute("SELECT discord_id FROM players WHERE identity_id = ?", (identity_num,))
                rec_player = c.fetchone()
                if rec_player:
                    recipient_discord_id = rec_player[0]
            except ValueError:
                pass

        if not recipient_discord_id:
            await interaction.followup.send("❌ لم يتم العثور على حساب أو هوية بهذا الرقم أو الآيبان!", ephemeral=True)
            return

        if recipient_discord_id == sender_id:
            await interaction.followup.send("❌ لا يمكنك التحويل لنفسك!", ephemeral=True)
            return

        # تنفيذ عملية التحويل
        c.execute("UPDATE bank_accounts SET balance = balance - ? WHERE discord_id = ?", (transfer_amount, sender_id))
        c.execute("UPDATE bank_accounts SET balance = balance + ? WHERE discord_id = ?", (transfer_amount, recipient_discord_id))
        conn.commit()

        embed = discord.Embed(
            title="🔄 - Transfer Success",
            description=f"✅ تم تحويل مبلغ `{transfer_amount} $` بنجاح إلى الحساب المستهدف!",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

class ChangeDataView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="تغيير البيانات", style=discord.ButtonStyle.secondary, emoji="✏️")
    async def change_data(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="⚙️ - Settings",
            description="ميزة تعديل البيانات قيد التفعيل...",
            color=discord.Color.from_str("#111111")
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class CreateBankAccountModal(discord.ui.Modal, title='إنشاء حساب بنكي'):
    account_name = discord.ui.TextInput(label='اسم الحساب البنكي', placeholder='أدخل اسم الحساب...')
    pin_code = discord.ui.TextInput(label='الرقم السرى (Pin)', placeholder='أدخل الأرقام السرية...', style=discord.TextStyle.short)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        acc_name = self.account_name.value.strip()
        pin = self.pin_code.value.strip()

        c.execute("SELECT 1 FROM bank_accounts WHERE discord_id = ?", (user_id,))
        if c.fetchone():
            embed_err = discord.Embed(title="❌ - Error", description="لديك حساب بنكي مسجل مسبقاً بالفعل!", color=discord.Color.red())
            await interaction.followup.send(embed=embed_err, ephemeral=True)
            return

        iban = f"IB{random.randint(100000, 999999)}"

        c.execute("INSERT INTO bank_accounts (discord_id, account_name, pin_code, iban, balance) VALUES (?, ?, ?, ?, ?)", 
                  (user_id, acc_name, pin, iban, 5000))
        conn.commit()

        try:
            embed_dm = discord.Embed(
                title="Your Account",
                description=(
                    f"• **Your Account :**\n\n"
                    f"**Card Name :** {acc_name}\n\n"
                    f"**Password :** {pin}\n\n"
                    f"**Iban :** {iban}"
                ),
                color=discord.Color.from_str("#111111")
            )
            embed_dm.set_footer(text="© Effect Kings System | 2026")
            await interaction.user.send(embed=embed_dm, view=ChangeDataView())
            
            embed_success = discord.Embed(title="✅ - Success", description="تم إنشاء حسابك البنكي وإرسال تفاصيل الحساب إلى رسائلك الخاصة (DM)!", color=discord.Color.green())
            await interaction.followup.send(embed=embed_success, ephemeral=True)
        except Exception:
            embed_warn = discord.Embed(title="⚠️ - Warning", description="تم إنشاء حسابك بنجاح، ولكن تعذر إرسال الرسالة الخاصة تأكد من فتح رسائلك الخاصة (DM).", color=discord.Color.orange())
            await interaction.followup.send(embed=embed_warn, ephemeral=True)

        log_channel = bot.get_channel(BANK_LOG_CHANNEL_ID)
        if log_channel:
            embed_log = discord.Embed(
                title="📝 | سجل جديد: إنشاء حساب بنكي",
                description=(
                    f"👤 **العضو:** {interaction.user.mention}\n"
                    f"📂 **اسم الحساب:** `{acc_name}`\n"
                    f"💳 **الآيبان:** `{iban}`\n"
                    f"💰 **الرصيد الابتدائي:** `5000 $`"
                ),
                color=discord.Color.green()
            )
            await log_channel.send(embed=embed_log)

class BankServicesView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="Money", style=discord.ButtonStyle.primary, emoji="💰", row=0)
    async def check_money(self, interaction: discord.Interaction, button: discord.ui.Button):
        c.execute("SELECT account_name, balance, iban FROM bank_accounts WHERE discord_id = ?", (interaction.user.id,))
        acc = c.fetchone()
        if not acc:
            embed_err = discord.Embed(title="❌ - Error", description="ليس لديك حساب بنكي!", color=discord.Color.red())
            await interaction.response.send_message(embed=embed_err, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="💰 - Bank Balance",
            description=f"📂 **الحساب:** `{acc[0]}`\n💳 **الآيبان:** `{acc[2]}`\n💵 **الرصيد المتوفر:** `{acc[1]} $`",
            color=discord.Color.from_str("#111111")
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Transfer", style=discord.ButtonStyle.success, emoji="🏦", row=0)
    async def transfer_money(self, interaction: discord.Interaction, button: discord.ui.Button):
        c.execute("SELECT 1 FROM bank_accounts WHERE discord_id = ?", (interaction.user.id,))
        if not c.fetchone():
            await interaction.response.send_message("❌ ليس لديك حساب بنكي لتحويل الأموال!", ephemeral=True)
            return
        await interaction.response.send_modal(TransferModal())

    @discord.ui.button(label="Deposit", style=discord.ButtonStyle.success, emoji="💵", row=1)
    async def deposit_money(self, interaction: discord.Interaction, button: discord.ui.Button):
        c.execute("SELECT 1 FROM bank_accounts WHERE discord_id = ?", (interaction.user.id,))
        if not c.fetchone():
            await interaction.response.send_message("❌ ليس لديك حساب بنكي للإيداع فيه!", ephemeral=True)
            return
        await interaction.response.send_modal(DepositModal())

    @discord.ui.button(label="Withdraw", style=discord.ButtonStyle.success, emoji="💳", row=1)
    async def withdraw_money(self, interaction: discord.Interaction, button: discord.ui.Button):
        c.execute("SELECT 1 FROM bank_accounts WHERE discord_id = ?", (interaction.user.id,))
        if not c.fetchone():
            await interaction.response.send_message("❌ ليس لديك حساب بنكي للسحب منه!", ephemeral=True)
            return
        await interaction.response.send_modal(WithdrawModal())

class MainBankView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Gold Bank", style=discord.ButtonStyle.primary, emoji="🏦", row=0)
    async def gold_bank(self, interaction: discord.Interaction, button: discord.ui.Button):
        c.execute("SELECT 1 FROM bank_accounts WHERE discord_id = ?", (interaction.user.id,))
        if not c.fetchone():
            embed_err = discord.Embed(title="❌ - Error", description="ليس لديك حساب بنكي! الرجاء الضغط على زر **Create Bank** لإنشاء حسابك أولاً.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed_err, ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🏛️ - Bank System",
            description="اختر الخدمة التي تريدها من البنك",
            color=discord.Color.from_str("#111111")
        )
        embed.set_footer(text="© Effect Kings System | 2026")
        await interaction.response.send_message(embed=embed, view=BankServicesView(interaction.user.id), ephemeral=True)

    @discord.ui.button(label="Create Bank", style=discord.ButtonStyle.success, emoji="💳", row=0)
    async def create_bank(self, interaction: discord.Interaction, button: discord.ui.Button):
        c.execute("SELECT 1 FROM bank_accounts WHERE discord_id = ?", (interaction.user.id,))
        if c.fetchone():
            embed_err = discord.Embed(title="❌ - Error", description="لديك حساب بنكي مسجل مسبقاً بالفعل!", color=discord.Color.red())
            await interaction.response.send_message(embed=embed_err, ephemeral=True)
            return
        await interaction.response.send_modal(CreateBankAccountModal())

    @discord.ui.button(label="Choose Your Account", style=discord.ButtonStyle.secondary, emoji="⚙️", row=1)
    async def choose_account(self, interaction: discord.Interaction, button: discord.ui.Button):
        c.execute("SELECT account_name, pin_code, iban, balance FROM bank_accounts WHERE discord_id = ?", (interaction.user.id,))
        acc = c.fetchone()
        if acc:
            embed = discord.Embed(
                title="Your Account",
                description=(
                    f"• **Your Account :**\n\n"
                    f"**Card Name :** {acc[0]}\n\n"
                    f"**Password :** {acc[1]}\n\n"
                    f"**Iban :** {acc[2]}\n\n"
                    f"**Balance :** {acc[3]} $"
                ),
                color=discord.Color.from_str("#111111")
            )
            embed.set_footer(text="© Effect Kings System | 2026")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed_err = discord.Embed(title="❌ - Error", description="ليس لديك أي حساب بنكي مسجل. اضغط على **Create Bank** لإنشاء حساب.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed_err, ephemeral=True)

# ==================== الأوامر العامة (Commands) ====================

@bot.command(name="trip")
async def trip_command(ctx):
    if not has_trip_permission(ctx.author):
        await ctx.send("عذراً، لا تمتلك رتبة `GT | Trip Support` أو صلاحية الأدمن لاستخدام هذا الأمر.", delete_after=5)
        return

    try:
        await ctx.message.delete()
    except Exception:
        pass
    
    view = TripControlView()
    await ctx.send("✈️ **لوحة التحكم السريعة للرحلة (إدخال البيانات، بدء، تجديد، وإعصار):**", view=view)

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

@bot.command(name="bank")
async def bank_command(ctx):
    if not ctx.author.guild_permissions.administrator:
        return
    try:
        await ctx.message.delete()
    except Exception:
        pass

    embed = discord.Embed(
        title="💳 | Bank • Services",
        description=(
            "هذه هي خدمات البنك المتوفرة داخل السيرفر:\n\n"
            "💳 **| All members are required to create a bank account before using any financial services.**\n"
            "**Without a bank account, you will not be able to access transfers, deposits, withdrawals, or other banking features.**\n\n"
            "يجب على كل عضو إنشاء حساب بنكي للاستفادة من الخدمات المالية .\n"
            "يمكنك من خلال البنك إيداع الأموال وسحبها وتحويلها بين الحسابات .\n"
            "جميع العمليات المالية يتم تسجيلها ومتابعتها بشكل تلقائي .\n"
            "الحساب البنكي يساعدك على حفظ أموالك وإدارتها بشكل آمن .\n"
            "تتوفر خدمات إضافية أخرى متعلقة بالبنك والتمويل داخل السيرفر ."
        ),
        color=discord.Color.from_str("#111111")
    )
    embed.set_image(url=BANK_IMAGE_URL)
    embed.set_footer(text="© Effect Kings System | 2026")

    await ctx.send(embed=embed, view=MainBankView())

@bot.command(name="missing")
async def missing_characters(ctx):
    if not ctx.author.guild_permissions.administrator:
        return

    c.execute("SELECT discord_id FROM bank_accounts")
    registered_ids = {row[0] for row in c.fetchall()}

    missing_members = [m.mention for m in ctx.guild.members if not m.bot and m.id not in registered_ids]

    if missing_members:
        members_text = ", ".join(missing_members[:30])
        embed = discord.Embed(
            title="⚠️ | تنبيه الأعضاء الذين لم يسجلوا دخول بشخصية",
            description=f"الأعضاء التاليين لم يقوموا بإنشاء حساب بنكي حتى الآن:\n\n{members_text}",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
    else:
        embed_ok = discord.Embed(title="✅ - Complete", description="ممتاز، جميع الأعضاء قاموا بإنشاء حساباتهم!", color=discord.Color.green())
        await ctx.send(embed=embed_ok)

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
 
