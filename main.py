from discord.ext import commands, tasks
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
		                balance INTEGER DEFAULT 1000, 
		                status TEXT,
		                health_status TEXT DEFAULT 'healthy',
		                has_insurance BOOLEAN DEFAULT FALSE,
		                mining_level INTEGER DEFAULT 1,
		                mining_count INTEGER DEFAULT 0,
		                heist_progress INTEGER DEFAULT 0
		            )''')

c.execute('''CREATE TABLE IF NOT EXISTS trips (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             discord_id INTEGER,
             status TEXT
          )''')

c.execute('''CREATE TABLE IF NOT EXISTS server_config (
             key TEXT PRIMARY KEY,
             value TEXT
          )''')

c.execute("INSERT OR IGNORE INTO server_config (key, value) VALUES ('trip_active', 'false')")

c.execute('''CREATE TABLE IF NOT EXISTS bank_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                discord_id INTEGER UNIQUE,
                account_name TEXT,
                pin_code TEXT,
                iban TEXT,
                balance INTEGER DEFAULT 5000
            )''')

c.execute('''CREATE TABLE IF NOT EXISTS user_inventory (
	                id INTEGER PRIMARY KEY AUTOINCREMENT,
	                discord_id INTEGER,
	                identity_id INTEGER,
	                item_key TEXT,
	                item_name TEXT,
	                item_count INTEGER,
	                item_image TEXT,
	                durability INTEGER DEFAULT 200
	            )''')

conn.commit()

async def trip_check(ctx):
    c.execute("SELECT value FROM server_config WHERE key = 'trip_active'")
    result = c.fetchone()
    trip_active = result[0] == 'true' if result else False
    if not trip_active:
        await ctx.send("❌ لا يمكنك استخدام هذا الأمر حالياً. الرحلة غير مفعلة.", ephemeral=True)
        return False
    return True

current_trip_status = False

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

LOG_CHANNEL_ID = 1530791985131032656
TARGET_VERIFY_CHANNEL_ID = 1530770263598301225  
REQUIRED_ROLE_NAME = "GT | Trip Support"

CHARACTER_SYSTEM_IMAGE = "https://cdn.discordapp.com/attachments/1530770369060016178/1531093153854001275/IMG__.jpg?ex=6a67f51e&is=6a66a39e&hm=a1fa106680e5411b414810d4de090c586add9f6e4df1d137ec651dfe4233056b&"
BANK_IMAGE_URL = "https://cdn.discordapp.com/attachments/1530770369060016178/1531093153854001275/IMG__.jpg?ex=6a67f51e&is=6a66a39e&hm=a1fa106680e5411b414810d4de090c586add9f6e4df1d137ec651dfe4233056b&"
HOSPITAL_IMAGE_URL = "https://cdn.discordapp.com/attachments/1531468959260475412/1531476076591845528/IMG__.jpg?ex=6a6959be&is=6a68083e&hm=129e0a44273589aa70ba6e1b731e8fc5202a0d6ad576e06526f65465e185ea73&"
HOSPITAL_LOG_CHANNEL_ID = 1531468959260475412
IKEA_LOG_CHANNEL_ID = 1531481688079863858
INVENTORY_LOG_CHANNEL_ID = 1531481825183010946
AMBULANCE_ROLE_NAME = "GT | Ambulance"
GT_POLICE_ROLE_NAME = "GT | Police👮"
POLICE_LOG_CHANNEL_ID = 1530770417466478819
RESUSCITATION_COST = 5000
POLICE_SALARY = 8000
MEDIC_SALARY = 6000

HEIST_CONFIG = {
    "ATM": {
        "min_reward": 500, "max_reward": 1500, "requirement": "لوكبك", "progress_needed": 0, "difficulty": 1,
        "location": "شارع Legion Square",
        "rob_image": "https://i.postimg.cc/qR1Zk0qP/atm-rob.png"
    },
    "Grocery": {
        "min_reward": 2000, "max_reward": 5000, "requirement": "لوكبك", "progress_needed": 1, "difficulty": 2, "key_reward": "مفتاح محل الملابس",
        "location": "بقالة 24/7 - طريق سريع",
        "rob_image": "https://i.postimg.cc/8cM2tZ0n/grocery-rob.png"
    },
    "Clothing": {
        "min_reward": 7000, "max_reward": 15000, "requirement": "مفتاح محل الملابس", "progress_needed": 2, "difficulty": 3, "key_reward": "مفتاح السرقات الكبرى",
        "location": "محل ملابس Binco - وسط المدينة",
        "rob_image": "https://i.postimg.cc/j5P0Y0nJ/clothing-rob.png"
    }
}

HEIST_IMAGE_URL = "https://cdn.discordapp.com/attachments/1531468959260475412/1531476076591845528/IMG__.jpg?ex=6a6959be&is=6a68083e&hm=129e0a44273589aa70ba6e1b731e8fc5202a0d6ad576e06526f65465e185ea73&"
HOSPITAL_RESUSCITATION_COST = 10000
MEDICAL_INSURANCE_COST = 20000
WITCH_RESUSCITATION_COST = 3000

CAR_SHOWROOM_IMAGE_URL = "https://cdn.discordapp.com/attachments/1531468959260475412/1531476076591845528/IMG__.jpg?ex=6a6959be&is=6a68083e&hm=129e0a44273589aa70ba6e1b731e8fc5202a0d6ad576e06526f65465e185ea73&"
CARS = {
    "Albany Primo": {"price": 5000, "image": "https://i.imgur.com/example1.png"},
    "Sultan Classic": {"price": 25000, "image": "https://i.imgur.com/example2.png"},
    "Sultan RS": {"price": 45000, "image": "https://i.imgur.com/example3.png"},
    "Elegy Retro Custom (Skyline)": {"price": 85000, "image": "https://i.imgur.com/example4.png"},
    "Ubermacht Oracle XS (BMW Large)": {"price": 60000, "image": "https://i.imgur.com/example5.png"},
    "Canis Mesa (Wrangler)": {"price": 35000, "image": "https://i.imgur.com/example6.png"},
    "Karin Futo (Drift Classic)": {"price": 15000, "image": "https://i.imgur.com/example7.png"},
    "Vapid Stanier (Police/Taxi Style)": {"price": 8000, "image": "https://i.imgur.com/example8.png"}
}

IKEA_IMAGE_URL = "https://cdn.discordapp.com/attachments/1531468959260475412/1531476076591845528/IMG__.jpg?ex=6a6959be&is=6a68083e&hm=129e0a44273589aa70ba6e1b731e8fc5202a0d6ad576e06526f65465e185ea73&"
IKEA_ITEMS = {
    "جوال": {"price": 800, "image": "https://i.imgur.com/phone_thumb.png"},
    "لوكبك": {"price": 500, "image": "https://i.imgur.com/lockpick_thumb.png"},
    "راديو": {"price": 800, "image": "https://i.imgur.com/radio_thumb.png"},
    "فأس": {"price": 1200, "image": "https://i.imgur.com/pickaxe_thumb.png"},
    "حبل": {"price": 200, "image": "https://i.imgur.com/rope_thumb.png"},
    "لاصق": {"price": 100, "image": "https://i.imgur.com/tape_thumb.png"},
    "مظلة": {"price": 2500, "image": "https://i.imgur.com/parachute_thumb.png"},
    "أداة غوص": {"price": 3000, "image": "https://i.imgur.com/diving_thumb.png"},
    "سنارة": {"price": 1000, "image": "https://i.postimg.cc/mD4Qx9wV/fishing-rod.png"},
    "فأس خشب": {"price": 1200, "image": "https://i.postimg.cc/Nj0n0wXN/hatchet.png"}
}

FISHING_IMAGE_URL = "https://cdn.discordapp.com/attachments/1531468959260475412/1531476076591845528/IMG__.jpg?ex=6a6959be&is=6a68083e&hm=129e0a44273589aa70ba6e1b731e8fc5202a0d6ad576e06526f65465e185ea73&"
WOODCUTTING_IMAGE_URL = "https://cdn.discordapp.com/attachments/1531468959260475412/1531476076591845528/IMG__.jpg?ex=6a6959be&is=6a68083e&hm=129e0a44273589aa70ba6e1b731e8fc5202a0d6ad576e06526f65465e185ea73&"

FISHING_RESOURCES = {
    "Rare Fish": {"price": 800, "chance": 10, "image": "https://i.postimg.cc/qR1Zk0qP/rare-fish.png"},
    "Large Fish": {"price": 400, "chance": 30, "image": "https://i.postimg.cc/8cM2tZ0n/large-fish.png"},
    "Common Fish": {"price": 150, "chance": 60, "image": "https://i.postimg.cc/j5P0Y0nJ/common-fish.png"}
}

WOOD_RESOURCES = {
    "Oak Wood": {"price": 300, "chance": 30, "image": "https://i.postimg.cc/zX0n0wXN/oak-wood.png"},
    "Plain Wood": {"price": 100, "chance": 70, "image": "https://i.postimg.cc/Nj0n0wXN/plain-wood.png"}
}

MINING_IMAGE_URL = "https://cdn.discordapp.com/attachments/1531468959260475412/1531476076591845528/IMG__.jpg?ex=6a6959be&is=6a68083e&hm=129e0a44273589aa70ba6e1b731e8fc5202a0d6ad576e06526f65465e185ea73&"
MINING_LOG_CHANNEL_ID = 1531481688079863858 # سنستخدم نفس لوق ايكيا مؤقتاً أو يمكنك تغييره

MINING_RESOURCES = {
    "Diamond": {"price": 1000, "chance": 5, "image": "https://i.postimg.cc/8PzQ0HkY/diamond-icon.png"},
    "Gold": {"price": 500, "chance": 15, "image": "https://i.postimg.cc/kX4L7P4t/gold-ingot.png"},
    "Iron": {"price": 200, "chance": 30, "image": "https://i.postimg.cc/7Z9Y3v7G/iron-ingot.png"},
    "Coal": {"price": 50, "chance": 50, "image": "https://i.postimg.cc/0jXqQ2zY/coal-icon.png"}
}

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    for guild in bot.guilds:
        await setup_server_permissions(guild)
    
    # تسجيل الـ Views كـ Persistent لكي تعمل دائماً ولا تفقد الاستجابة
    bot.add_view(CharacterView())
    bot.add_view(MainBankView())
    bot.add_view(HospitalView())
    bot.add_view(CarShowroomView())
    bot.add_view(IkeaStoreView())
    bot.add_view(TicketView())
    
    print("Bot is online and running successfully with persistent views!")
    give_salaries.start()

@tasks.loop(hours=168) # تشغيل المهمة كل أسبوع (168 ساعة)
async def give_salaries():
    await bot.wait_until_ready()
    print("بدء مهمة توزيع الرواتب الأسبوعية...")
    for guild in bot.guilds:
        police_role = discord.utils.get(guild.roles, name=GT_POLICE_ROLE_NAME)
        ambulance_role = discord.utils.get(guild.roles, name=AMBULANCE_ROLE_NAME)

        if not police_role or not ambulance_role:
            print(f"لم يتم العثور على رتب الشرطة أو الإسعاف في {guild.name}")
            continue

        for member in guild.members:
            if police_role in member.roles:
                c.execute("UPDATE players SET balance = balance + ? WHERE discord_id = ?", (POLICE_SALARY, member.id))
                conn.commit()
                print(f"تم دفع راتب الشرطي {member.name}: {POLICE_SALARY}")
                try:
                    await member.send(f"✅ تم إيداع راتبك الأسبوعي كشرطي ({POLICE_SALARY} دولار) في حسابك.")
                except:
                    pass
            elif ambulance_role in member.roles:
                c.execute("UPDATE players SET balance = balance + ? WHERE discord_id = ?", (MEDIC_SALARY, member.id))
                conn.commit()
                print(f"تم دفع راتب المسعف {member.name}: {MEDIC_SALARY}")
                try:
                    await member.send(f"✅ تم إيداع راتبك الأسبوعي كمسعف ({MEDIC_SALARY} دولار) في حسابك.")
                except:
                    pass
    print("انتهت مهمة توزيع الرواتب الأسبوعية.")

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
            await message.delete()
        except Exception:
            pass

        try:
            guild = message.guild
            member = message.author
            content = message.content.strip()
            
            try:
                await member.edit(nick=content)
            except Exception as nick_err:
                print(f"Note: Could not change nickname: {nick_err}")
            
            verified_role = discord.utils.get(guild.roles, name="Verified")
            unverified_role = discord.utils.get(guild.roles, name="Unverified")
            inactive_role = discord.utils.get(guild.roles, name="Inactive")
            
            if verified_role and verified_role not in member.roles:
                await member.add_roles(verified_role)
            if unverified_role and unverified_role in member.roles:
                await member.remove_roles(unverified_role)
            if inactive_role and inactive_role in member.roles:
                await member.remove_roles(inactive_role)
                
            await message.channel.send(f"🟡 تم تفعيلك بنجاح يا {member.mention}! وتم تحديث اسمك إلى `{content}` وإزالة رتبة Inactive.", delete_after=5)
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
            
        await interaction.followup.send(f"🟡 مبروك! اجتازت شخصيتك كافة الشروط وتم **قبولها وحفظها بقاعدة البيانات بنجاح**.", ephemeral=True)

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
        super().__init__(timeout=180)
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
            await interaction.response.send_message(f"🟡 تم تسجيل الخروج من الشخصية: `{char_name}` بنجاح مع حفظ كافة بياناتها وأغراضها.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ حدث خطأ أثناء تسجيل الخروج: {e}", ephemeral=True)

class LogoutSelectView(discord.ui.View):
    def __init__(self, players):
        super().__init__(timeout=180)
        self.add_item(LogoutSelect(players))

class CharacterSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Create Character", description="إنشاء شخصية جديدة ومحفوظة بالكامل"),
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
                text = "هوياتك المسجلة والمحفوظة بقاعدة البيانات:\n"
                for idx, p in enumerate(players, 1):
                    text += f"\n**الشخصية {idx}:**\n- 👤 الاسم: `{p[1]} {p[2]}`\n- 🆔 رقم الهوية: `{p[0]}`\n- 📅 المواليد: `{p[3]}`\n- ⚧️ الجنس: `{p[4]}`\n- 📍 مكان الولادة: `{p[5]}`\n- 💰 الكاش: `{p[6]} $`\n"
                await interaction.followup.send(text, ephemeral=True)
            else:
                await interaction.followup.send("❌ ليس لديك أي شخصيات مسجلة!", ephemeral=True)

class CharacterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # تفعيل وقت غير محدود (دائم) لكي لا تنتهي صلاحية الأزرار
        self.add_item(CharacterSelect())

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
        c.execute("SELECT id, balance FROM players WHERE discord_id = ? ORDER BY id ASC LIMIT 1", (user_id,))
        player = c.fetchone()
        
        if not player:
            await interaction.followup.send("❌ ليس لديك أي شخصية مسجلة لتسحب منها الكاش!", ephemeral=True)
            return
        
        player_db_id, player_cash = player[0], player[1]

        if deposit_amount > player_cash:
            await interaction.followup.send("❌ ماعندك أموال كافيه في الكاش!", ephemeral=True)
            return

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
        c.execute("SELECT balance FROM bank_accounts WHERE discord_id = ?", (sender_id,))
        sender_bank = c.fetchone()
        if not sender_bank:
            await interaction.followup.send("❌ ليس لديك حساب بنكي!", ephemeral=True)
            return
        
        if transfer_amount > sender_bank[0]:
            await interaction.followup.send("❌ رصيدك في البنك لا يكفي لإتمام عملية التحويل!", ephemeral=True)
            return

        recipient_discord_id = None
        c.execute("SELECT discord_id FROM bank_accounts WHERE iban = ?", (target_input,))
        rec_acc = c.fetchone()
        if rec_acc:
            recipient_discord_id = rec_acc[0]
        else:
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

        c.execute("UPDATE bank_accounts SET balance = balance - ? WHERE discord_id = ?", (transfer_amount, sender_id))
        c.execute("UPDATE bank_accounts SET balance = balance + ? WHERE discord_id = ?", (transfer_amount, recipient_discord_id))
        conn.commit()

        embed = discord.Embed(
            title="🔄 - Transfer Success",
            description=f"✅ تم تحويل مبلغ `{transfer_amount} $` بنجاح إلى الحساب المستهدف!",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

class BankServicesView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=180)
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

class HospitalView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="إنعاش", style=discord.ButtonStyle.green, custom_id="resuscitate_button")
    async def resuscitate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        member = interaction.user

        c.execute("SELECT health_status, has_insurance FROM players WHERE discord_id = ?", (user_id,))
        player_data = c.fetchone()

        if not player_data:
            await interaction.followup.send("❌ لا تملك شخصية مسجلة. يرجى إنشاء شخصية أولاً.", ephemeral=True)
            return

        health_status, has_insurance = player_data

        if health_status == 'healthy':
            await interaction.followup.send("✅ أنت بصحة جيدة بالفعل! لا تحتاج إلى إنعاش.", ephemeral=True)
            return

        # Check for GT | Police👮 role for free resuscitation
        police_role = discord.utils.get(member.guild.roles, name=GT_POLICE_ROLE_NAME)
        if police_role and police_role in member.roles:
            c.execute("UPDATE players SET health_status = ? WHERE discord_id = ?", ('healthy', user_id))
            conn.commit()
            embed = discord.Embed(title="🚨 إنعاش مجاني (شرطة)", description=f"{member.mention} تم إنعاشك بنجاح بواسطة الشرطة!", color=discord.Color.green())
            embed.set_thumbnail(url=HOSPITAL_IMAGE_URL)
            embed.set_image(url=HOSPITAL_IMAGE_URL)
            log_channel = bot.get_channel(HOSPITAL_LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(embed=embed)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Paid resuscitation for others
        c.execute("SELECT balance FROM bank_accounts WHERE discord_id = ?", (user_id,))
        bank_balance = c.fetchone()

        if not bank_balance or bank_balance[0] < RESUSCITATION_COST:
            await interaction.followup.send(f"❌ ليس لديك رصيد كافٍ في البنك. تكلفة الإنعاش: `{RESUSCITATION_COST:,} $`", ephemeral=True)
            return

        c.execute("UPDATE bank_accounts SET balance = balance - ? WHERE discord_id = ?", (RESUSCITATION_COST, user_id))
        c.execute("UPDATE players SET health_status = ? WHERE discord_id = ?", ('healthy', user_id))
        conn.commit()

        embed = discord.Embed(title="🏥 إنعاش", description=f"{member.mention} تم إنعاشك بنجاح! تم خصم `{RESUSCITATION_COST:,} $` من حسابك.", color=discord.Color.green())
        embed.set_thumbnail(url=HOSPITAL_IMAGE_URL)
        embed.set_image(url=HOSPITAL_IMAGE_URL)
        log_channel = bot.get_channel(HOSPITAL_LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(embed=embed)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="إنعاش مستشفى", style=discord.ButtonStyle.blurple, custom_id="hospital_resuscitate_button")
    async def hospital_resuscitate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        member = interaction.user

        c.execute("SELECT health_status, has_insurance FROM players WHERE discord_id = ?", (user_id,))
        player_data = c.fetchone()

        if not player_data:
            await interaction.followup.send("❌ لا تملك شخصية مسجلة. يرجى إنشاء شخصية أولاً.", ephemeral=True)
            return

        health_status, has_insurance = player_data

        if health_status == 'healthy':
            await interaction.followup.send("✅ أنت بصحة جيدة بالفعل! لا تحتاج إلى إنعاش.", ephemeral=True)
            return

        cost = HOSPITAL_RESUSCITATION_COST
        if has_insurance:
            cost = int(cost * 0.5) # 50% discount with insurance

        c.execute("SELECT balance FROM bank_accounts WHERE discord_id = ?", (user_id,))
        bank_balance = c.fetchone()

        if not bank_balance or bank_balance[0] < cost:
            await interaction.followup.send(f"❌ ليس لديك رصيد كافٍ في البنك. تكلفة إنعاش المستشفى: `{cost:,} $`", ephemeral=True)
            return

        c.execute("UPDATE bank_accounts SET balance = balance - ? WHERE discord_id = ?", (cost, user_id))
        c.execute("UPDATE players SET health_status = ? WHERE discord_id = ?", ('healthy', user_id))
        conn.commit()

        embed = discord.Embed(title="🏥 إنعاش مستشفى", description=f"{member.mention} تم إنعاشك بنجاح في المستشفى! تم خصم `{cost:,} $` من حسابك.", color=discord.Color.blurple())
        if has_insurance:
            embed.add_field(name="تأمين طبي", value="تم تطبيق خصم 50%.", inline=False)
        embed.set_thumbnail(url=HOSPITAL_IMAGE_URL)
        embed.set_image(url=HOSPITAL_IMAGE_URL)
        log_channel = bot.get_channel(HOSPITAL_LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(embed=embed)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="إنعاش ساحرة", style=discord.ButtonStyle.red, custom_id="witch_resuscitate_button")
    async def witch_resuscitate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        member = interaction.user

        c.execute("SELECT health_status FROM players WHERE discord_id = ?", (user_id,))
        player_data = c.fetchone()

        if not player_data:
            await interaction.followup.send("❌ لا تملك شخصية مسجلة. يرجى إنشاء شخصية أولاً.", ephemeral=True)
            return

        health_status = player_data[0]

        if health_status == 'healthy':
            await interaction.followup.send("✅ أنت بصحة جيدة بالفعل! لا تحتاج إلى إنعاش.", ephemeral=True)
            return

        c.execute("SELECT balance FROM bank_accounts WHERE discord_id = ?", (user_id,))
        bank_balance = c.fetchone()

        if not bank_balance or bank_balance[0] < WITCH_RESUSCITATION_COST:
            await interaction.followup.send(f"❌ ليس لديك رصيد كافٍ في البنك. تكلفة إنعاش الساحرة: `{WITCH_RESUSCITATION_COST:,} $`", ephemeral=True)
            return

        c.execute("UPDATE bank_accounts SET balance = balance - ? WHERE discord_id = ?", (WITCH_RESUSCITATION_COST, user_id))
        c.execute("UPDATE players SET health_status = ? WHERE discord_id = ?", ('healthy', user_id))
        conn.commit()

        embed = discord.Embed(title="🔮 إنعاش ساحرة", description=f"{member.mention} تم إنعاشك بنجاح بواسطة الساحرة! تم خصم `{WITCH_RESUSCITATION_COST:,} $` من حسابك.", color=discord.Color.red())
        embed.set_thumbnail(url=HOSPITAL_IMAGE_URL)
        embed.set_image(url=HOSPITAL_IMAGE_URL)
        log_channel = bot.get_channel(HOSPITAL_LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(embed=embed)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="إنعاش ساحرة", style=discord.ButtonStyle.red, custom_id="witch_resuscitate_button")
    async def witch_resuscitate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        member = interaction.user

        c.execute("SELECT health_status FROM players WHERE discord_id = ?", (user_id,))
        player_data = c.fetchone()

        if not player_data:
            await interaction.followup.send("❌ لا تملك شخصية مسجلة. يرجى إنشاء شخصية أولاً.", ephemeral=True)
            return

        health_status = player_data[0]

        if health_status == 'healthy':
            await interaction.followup.send("✅ أنت بصحة جيدة بالفعل! لا تحتاج إلى إنعاش.", ephemeral=True)
            return

        c.execute("SELECT balance FROM bank_accounts WHERE discord_id = ?", (user_id,))
        bank_balance = c.fetchone()

        if not bank_balance or bank_balance[0] < WITCH_RESUSCITATION_COST:
            await interaction.followup.send(f"❌ ليس لديك رصيد كافٍ في البنك. تكلفة إنعاش الساحرة: `{WITCH_RESUSCITATION_COST:,} $`", ephemeral=True)
            return

        c.execute("UPDATE bank_accounts SET balance = balance - ? WHERE discord_id = ?", (WITCH_RESUSCITATION_COST, user_id))
        c.execute("UPDATE players SET health_status = ? WHERE discord_id = ?", ('healthy', user_id))
        conn.commit()

        embed = discord.Embed(title="🔮 إنعاش ساحرة", description=f"{member.mention} تم إنعاشك بنجاح بواسطة الساحرة! تم خصم `{WITCH_RESUSCITATION_COST:,} $` من حسابك.", color=discord.Color.red())
        embed.set_thumbnail(url=HOSPITAL_IMAGE_URL)
        embed.set_image(url=HOSPITAL_IMAGE_URL)
        log_channel = bot.get_channel(HOSPITAL_LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(embed=embed)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="تأمين طبي", style=discord.ButtonStyle.primary, custom_id="medical_insurance_button")
    async def medical_insurance_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        member = interaction.user

        c.execute("SELECT has_insurance FROM players WHERE discord_id = ?", (user_id,))
        player_data = c.fetchone()

        if not player_data:
            await interaction.followup.send("❌ لا تملك شخصية مسجلة. يرجى إنشاء شخصية أولاً.", ephemeral=True)
            return

        has_insurance = player_data[0]

        if has_insurance:
            await interaction.followup.send("✅ أنت مؤمن صحياً بالفعل!", ephemeral=True)
            return

        c.execute("SELECT balance FROM bank_accounts WHERE discord_id = ?", (user_id,))
        bank_balance = c.fetchone()

        if not bank_balance or bank_balance[0] < MEDICAL_INSURANCE_COST:
            await interaction.followup.send(f"❌ ليس لديك رصيد كافٍ في البنك. تكلفة التأمين الطبي: `{MEDICAL_INSURANCE_COST:,} $`", ephemeral=True)
            return

        c.execute("UPDATE bank_accounts SET balance = balance - ? WHERE discord_id = ?", (MEDICAL_INSURANCE_COST, user_id))
        c.execute("UPDATE players SET has_insurance = ? WHERE discord_id = ?", (True, user_id))
        conn.commit()

        embed = discord.Embed(title="✅ تأمين طبي", description=f"{member.mention} تم شراء التأمين الطبي بنجاح! تم خصم `{MEDICAL_INSURANCE_COST:,} $` من حسابك.", color=discord.Color.green())
        embed.set_thumbnail(url=HOSPITAL_IMAGE_URL)
        embed.set_image(url=HOSPITAL_IMAGE_URL)
        log_channel = bot.get_channel(HOSPITAL_LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(embed=embed)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="تحلل", style=discord.ButtonStyle.red, custom_id="decompose_button")
    async def decompose_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        member = interaction.user

        c.execute("SELECT health_status, has_insurance FROM players WHERE discord_id = ?", (user_id,))
        player_data = c.fetchone()

        if not player_data:
            await interaction.followup.send("❌ لا تملك شخصية مسجلة.", ephemeral=True)
            return

        health_status, has_insurance = player_data

        if not has_insurance:
            # If no insurance, clear cash and inventory
            c.execute("UPDATE players SET balance = 0 WHERE discord_id = ?", (user_id,))
            c.execute("DELETE FROM user_inventory WHERE discord_id = ?", (user_id,))
            log_message = "فقدت كل الكاش والأغراض في شنطتك!"
        else:
            log_message = ""

        c.execute("UPDATE players SET health_status = ?, has_insurance = ? WHERE discord_id = ?", ('dead', False, user_id))
        conn.commit()

        embed = discord.Embed(title="💀 تحلل", description=f"{member.mention} تم تحلل شخصيتك. فقدت التأمين الصحي وأصبحت بحاجة للإنعاش. {log_message}", color=discord.Color.red())
        embed.set_thumbnail(url=HOSPITAL_IMAGE_URL)
        embed.set_image(url=HOSPITAL_IMAGE_URL)
        log_channel = bot.get_channel(HOSPITAL_LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(embed=embed)
        await interaction.followup.send(embed=embed, ephemeral=True)


class CarSelect(discord.ui.Select):
    def __init__(self):
        options = []
        for car_name, car_data in CARS.items():
            options.append(discord.SelectOption(label=car_name, description=f"السعر: {car_data["price"]:,} $", value=car_name))
        super().__init__(placeholder="اختر السيارة التي ترغب في عرضها...", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        selected_car_name = self.values[0]
        car_data = CARS.get(selected_car_name)

        if car_data:
            embed = discord.Embed(title=f"🚗 {selected_car_name}", color=discord.Color.gold())
            embed.add_field(name="السعر", value=f"`{car_data["price"]:,} $`", inline=False)
            embed.set_image(url=car_data["image"])
            embed.set_footer(text="© Gold Town System | 2026")
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send("❌ لم يتم العثور على معلومات لهذه السيارة.", ephemeral=True)

class CarShowroomView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CarSelect())

class IkeaPurchaseModal(discord.ui.Modal, title='تحديد كمية الشراء'):
    quantity = discord.ui.TextInput(label='الكمية المطلوبة', placeholder='أدخل العدد هنا (مثال: 1, 5, 10)...', min_length=1, max_length=3)

    def __init__(self, item_name, item_price, item_image):
        super().__init__()
        self.item_name = item_name
        self.item_price = item_price
        self.item_image = item_image

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user_id = interaction.user.id
        
        try:
            qty = int(self.quantity.value)
            if qty <= 0: raise ValueError
        except ValueError:
            await interaction.followup.send("❌ يرجى إدخال كمية صحيحة (رقم أكبر من صفر).", ephemeral=True)
            return

        total_price = self.item_price * qty

        # Check cash balance (from players table)
        c.execute("SELECT balance, identity_id FROM players WHERE discord_id = ? LIMIT 1", (user_id,))
        player_row = c.fetchone()
        
        if not player_row:
            await interaction.followup.send("❌ يجب أن يكون لديك شخصية مسجلة لتتمكن من الشراء.", ephemeral=True)
            return
            
        cash_balance, identity_id = player_row
        
        if cash_balance < total_price:
            await interaction.followup.send(f"❌ ليس لديك كاش كافٍ. التكلفة الإجمالية: `{total_price:,} $` | رصيدك الحالي: `{cash_balance:,} $`", ephemeral=True)
            return

        # Deduct cash
        c.execute("UPDATE players SET balance = balance - ? WHERE discord_id = ?", (total_price, user_id))
        
        # Add to inventory
        c.execute("SELECT item_count FROM user_inventory WHERE discord_id = ? AND item_name = ?", (user_id, self.item_name))
        inv_row = c.fetchone()
        if inv_row:
            c.execute("UPDATE user_inventory SET item_count = item_count + ? WHERE discord_id = ? AND item_name = ?", (qty, user_id, self.item_name))
        else:
            c.execute("INSERT INTO user_inventory (discord_id, identity_id, item_key, item_name, item_count, item_image) VALUES (?, ?, ?, ?, ?, ?)",
                      (user_id, identity_id, self.item_name, self.item_name, qty, self.item_image))
        
        conn.commit()

        embed = discord.Embed(title="🛒 تم الشراء بنجاح", description=f"لقد قمت بشراء **({qty}) {self.item_name}** بنجاح!", color=discord.Color.green())
        embed.add_field(name="المبلغ المخصوم (كاش)", value=f"`{total_price:,} $`", inline=False)
        embed.set_thumbnail(url=self.item_image)
        embed.set_footer(text="© Gold Town System | 2026")
        
        # Send log to IKEA log channel
        log_channel = bot.get_channel(IKEA_LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(title="🛒 سجل شراء ايكيا", color=discord.Color.gold())
            log_embed.add_field(name="المشتري", value=interaction.user.mention, inline=True)
            log_embed.add_field(name="رقم الهوية", value=f"`{identity_id}`", inline=True)
            log_embed.add_field(name="الغرض", value=self.item_name, inline=True)
            log_embed.add_field(name="الكمية", value=f"`{qty}`", inline=True)
            log_embed.add_field(name="التكلفة الإجمالية", value=f"`{total_price:,} $` (كاش)", inline=False)
            log_embed.set_footer(text=f"ID: {interaction.user.id}")
            await log_channel.send(embed=log_embed)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

class IkeaItemSelect(discord.ui.Select):
    def __init__(self):
        options = []
        for item_name, item_data in IKEA_ITEMS.items():
            options.append(discord.SelectOption(label=item_name, description=f"السعر: {item_data["price"]:,} $", value=item_name))
        super().__init__(placeholder="اختر الأداة التي ترغب في عرضها...", options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_item_name = self.values[0]
        item_data = IKEA_ITEMS.get(selected_item_name)

        if item_data:
            embed = discord.Embed(title=f"🛒 {selected_item_name}", color=discord.Color.gold())
            embed.add_field(name="السعر للقطعة", value=f"`{item_data["price"]:,} $`", inline=False)
            embed.set_image(url=item_data["image"])
            embed.set_footer(text="© Gold Town System | 2026")
            
            view = discord.ui.View()
            buy_button = discord.ui.Button(label="شراء الآن", style=discord.ButtonStyle.green, custom_id=f"buy_{selected_item_name}")
            
            async def buy_callback(inter: discord.Interaction):
                await inter.response.send_modal(IkeaPurchaseModal(selected_item_name, item_data["price"], item_data["image"]))
            
            buy_button.callback = buy_callback
            view.add_item(buy_button)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            await interaction.response.send_message("❌ لم يتم العثور على معلومات لهذه الأداة.", ephemeral=True)

class IkeaStoreView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(IkeaItemSelect())

class MiningSellSelect(discord.ui.Select):
    def __init__(self, user_items):
        options = []
        all_sellable = {**MINING_RESOURCES, **FISHING_RESOURCES, **WOOD_RESOURCES}
        for item_name, count in user_items:
            if item_name in all_sellable:
                price = all_sellable[item_name]["price"]
                options.append(discord.SelectOption(label=f"{item_name} (x{count})", description=f"سعر البيع: {price} $ للقطعة", value=item_name))
        
        if not options:
            options.append(discord.SelectOption(label="لا يوجد موارد للبيع", value="none", disabled=True))
            
        super().__init__(placeholder="اختر مورداً لبيعه...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none": return
        selected_item = self.values[0]
        user_id = interaction.user.id
        
        class SellQtyModal(discord.ui.Modal, title='بيع موارد المنجم'):
            qty = discord.ui.TextInput(label='الكمية المراد بيعها', placeholder='أدخل العدد هنا...', min_length=1, max_length=5)

            async def on_submit(self, modal_inter: discord.Interaction):
                try:
                    s_qty = int(self.qty.value)
                    if s_qty <= 0: raise ValueError
                except ValueError:
                    await modal_inter.response.send_message("❌ يرجى إدخال كمية صحيحة.", ephemeral=True)
                    return

                c.execute("SELECT item_count FROM user_inventory WHERE discord_id = ? AND item_name = ?", (user_id, selected_item))
                row = c.fetchone()
                if not row or row[0] < s_qty:
                    await modal_inter.response.send_message("❌ ليس لديك هذه الكمية في شنطتك.", ephemeral=True)
                    return

                all_sellable = {**MINING_RESOURCES, **FISHING_RESOURCES, **WOOD_RESOURCES}
                total_gain = s_qty * all_sellable[selected_item]["price"]
                
                # تنفيذ البيع
                if row[0] == s_qty:
                    c.execute("DELETE FROM user_inventory WHERE discord_id = ? AND item_name = ?", (user_id, selected_item))
                else:
                    c.execute("UPDATE user_inventory SET item_count = item_count - ? WHERE discord_id = ? AND item_name = ?", (s_qty, user_id, selected_item))
                
                c.execute("UPDATE players SET balance = balance + ? WHERE discord_id = ?", (total_gain, user_id))
                conn.commit()
                
                await modal_inter.response.send_message(f"💰 تم بيع **({s_qty}) {selected_item}** بنجاح مقابل **{total_gain:,} $** (كاش)!", ephemeral=True)

        await interaction.response.send_modal(SellQtyModal())

class MiningView(discord.ui.View):
    def __init__(self, user_items):
        super().__init__(timeout=None)
        self.add_item(MiningSellSelect(user_items))
        
    @discord.ui.button(label="بدء التعدين ⛏️", style=discord.ButtonStyle.green)
    async def mine_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # توجيه المستخدم لاستخدام الفأس من الشنطة
        await interaction.response.send_message("💡 لبدء التعدين، افتح شنطتك (`!شنطة`) واستخدم **الفأس** هناك!", ephemeral=True)

class InventoryItemSelect(discord.ui.Select):
    def __init__(self, items):
        options = []
        for item in items:
            item_name = item[0]
            item_count = item[1]
            options.append(discord.SelectOption(label=f"{item_name} (x{item_count})", value=item_name))
        super().__init__(placeholder="اختر غرضاً من الشنطة...", options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_item = self.values[0]
        user_id = interaction.user.id
        
        c.execute("SELECT item_count, item_image FROM user_inventory WHERE discord_id = ? AND item_name = ?", (user_id, selected_item))
        row = c.fetchone()
        if not row:
            await interaction.response.send_message("❌ هذا الغرض لم يعد موجوداً في شنطتك.", ephemeral=True)
            return
            
        count, image = row
        embed = discord.Embed(title=f"🎒 | {selected_item}", description=f"الكمية المتوفرة: **{count}**", color=discord.Color.gold())
        embed.set_thumbnail(url=image)
        embed.set_footer(text="© Gold Town System | 2026")
        
        view = discord.ui.View()
        use_btn = discord.ui.Button(label="استخدام", style=discord.ButtonStyle.green)
        give_btn = discord.ui.Button(label="إعطاء", style=discord.ButtonStyle.blurple)
        show_btn = discord.ui.Button(label="Show inv", style=discord.ButtonStyle.secondary)
        
        async def use_callback(inter):
            if selected_item == "فأس":
                await inter.response.defer(ephemeral=True)
                # منطق التعدين المطور
                c.execute("SELECT mining_level, mining_count, identity_id FROM players WHERE discord_id = ?", (user_id,))
                player_mining = c.fetchone()
                if not player_mining:
                    await inter.followup.send("❌ يجب أن يكون لديك شخصية مسجلة.", ephemeral=True)
                    return
                
                m_level, m_count, identity_id = player_mining
                
                # التحقق من متانة الفأس
                c.execute("SELECT durability, id FROM user_inventory WHERE discord_id = ? AND item_name = 'فأس' LIMIT 1", (user_id,))
                axe_row = c.fetchone()
                if not axe_row:
                    await inter.followup.send("❌ ليس لديك فأس في شنطتك!", ephemeral=True)
                    return
                
                axe_durability, axe_db_id = axe_row
                if axe_durability <= 0:
                    c.execute("DELETE FROM user_inventory WHERE id = ?", (axe_db_id,))
                    conn.commit()
                    await inter.followup.send("🪓 لقد انكسر الفأس الخاص بك! يجب شراء واحد جديد من ايكيا.", ephemeral=True)
                    return

                # عملية التعدين
                # تحديد المورد بناءً على الاحتمالات
                resource_roll = random.randint(1, 100)
                selected_resource = "Coal"
                if resource_roll <= 5: selected_resource = "Diamond"
                elif resource_roll <= 20: selected_resource = "Gold"
                elif resource_roll <= 50: selected_resource = "Iron"
                
                res_data = MINING_RESOURCES[selected_resource]
                
                # تحديد الكمية بناءً على اللفل
                if m_level >= 15:
                    amount = random.randint(40, 60)
                else:
                    amount = random.randint(1, 3)
                
                # تحديث المتانة واللفل
                new_durability = axe_durability - 1
                new_mining_count = m_count + 1
                new_level = m_level
                if new_mining_count >= 200:
                    new_level = m_level + 1
                    new_mining_count = 0
                
                c.execute("UPDATE user_inventory SET durability = ? WHERE id = ?", (new_durability, axe_db_id))
                c.execute("UPDATE players SET mining_level = ?, mining_count = ? WHERE discord_id = ?", (new_level, new_mining_count, user_id))
                
                # إضافة الموارد للشنطة
                c.execute("SELECT item_count FROM user_inventory WHERE discord_id = ? AND item_name = ?", (user_id, selected_resource))
                res_inv = c.fetchone()
                if res_inv:
                    c.execute("UPDATE user_inventory SET item_count = item_count + ? WHERE discord_id = ? AND item_name = ?", (amount, user_id, selected_resource))
                else:
                    c.execute("INSERT INTO user_inventory (discord_id, identity_id, item_key, item_name, item_count, item_image) VALUES (?, ?, ?, ?, ?, ?)",
                              (user_id, identity_id, selected_resource, selected_resource, amount, res_data["image"]))
                
                conn.commit()
                
                # إرسال النتيجة
                embed = discord.Embed(title="⛏️ عملية تعدين ناجحة", description=f"لقد قمت بالتنقيب في المنجم ووجدت موارد ثمينة!", color=discord.Color.dark_gray())
                embed.add_field(name="المورد المكتشف", value=f"**{selected_resource}**", inline=True)
                embed.add_field(name="الكمية", value=f"`{amount}` قطعة", inline=True)
                embed.add_field(name="حالة الفأس", value=f"المتانة المتبقية: `{new_durability}/200`", inline=False)
                if new_level > m_level:
                    embed.add_field(name="🆙 لفل أب!", value=f"لقد ارتفع مستواك في التعدين إلى لفل **{new_level}**!", inline=False)
                
                embed.set_image(url=MINING_IMAGE_URL)
                embed.set_thumbnail(url=res_data["image"])
                embed.set_footer(text="© Gold Town System | 2026")
                
                await inter.followup.send(embed=embed, ephemeral=True)
                
                # Log large mining or Diamond
                if selected_resource == "Diamond" or amount >= 40:
                    log_channel = bot.get_channel(MINING_LOG_CHANNEL_ID)
                    if log_channel:
                        log_embed = discord.Embed(title="⛏️ سجل تعدين مميز", color=discord.Color.blue())
                        log_embed.add_field(name="اللاعب", value=inter.user.mention, inline=True)
                        log_embed.add_field(name="المورد", value=selected_resource, inline=True)
                        log_embed.add_field(name="الكمية", value=str(amount), inline=True)
                        log_embed.add_field(name="اللفل الحالي", value=str(new_level), inline=True)
                        await log_channel.send(embed=log_embed)
            elif selected_item == "سنارة":
                await inter.response.defer(ephemeral=True)
                # منطق الصيد
                resource_roll = random.randint(1, 100)
                selected_fish = "Common Fish"
                if resource_roll <= 10: selected_fish = "Rare Fish"
                elif resource_roll <= 40: selected_fish = "Large Fish"
                
                res_data = FISHING_RESOURCES[selected_fish]
                amount = random.randint(1, 2)
                
                c.execute("SELECT identity_id FROM players WHERE discord_id = ?", (user_id,))
                identity_id = c.fetchone()[0]
                
                c.execute("SELECT item_count FROM user_inventory WHERE discord_id = ? AND item_name = ?", (user_id, selected_fish))
                res_inv = c.fetchone()
                if res_inv:
                    c.execute("UPDATE user_inventory SET item_count = item_count + ? WHERE discord_id = ? AND item_name = ?", (amount, user_id, selected_fish))
                else:
                    c.execute("INSERT INTO user_inventory (discord_id, identity_id, item_key, item_name, item_count, item_image) VALUES (?, ?, ?, ?, ?, ?)",
                              (user_id, identity_id, selected_fish, selected_fish, amount, res_data["image"]))
                conn.commit()
                
                embed = discord.Embed(title="🎣 عملية صيد ناجحة", description=f"لقد قمت بالصيد ونجحت في اصطياد شيء ما!", color=discord.Color.blue())
                embed.add_field(name="السمكة المكتشفة", value=f"**{selected_fish}**", inline=True)
                embed.add_field(name="الكمية", value=f"`{amount}` سمكة", inline=True)
                embed.set_image(url=FISHING_IMAGE_URL)
                embed.set_thumbnail(url=res_data["image"])
                embed.set_footer(text="© Gold Town System | 2026")
                await inter.followup.send(embed=embed, ephemeral=True)

            elif selected_item == "فأس خشب":
                await inter.response.defer(ephemeral=True)
                # منطق التحطيب
                resource_roll = random.randint(1, 100)
                selected_wood = "Plain Wood"
                if resource_roll <= 30: selected_wood = "Oak Wood"
                
                res_data = WOOD_RESOURCES[selected_wood]
                amount = random.randint(1, 3)
                
                c.execute("SELECT identity_id FROM players WHERE discord_id = ?", (user_id,))
                identity_id = c.fetchone()[0]
                
                c.execute("SELECT item_count FROM user_inventory WHERE discord_id = ? AND item_name = ?", (user_id, selected_wood))
                res_inv = c.fetchone()
                if res_inv:
                    c.execute("UPDATE user_inventory SET item_count = item_count + ? WHERE discord_id = ? AND item_name = ?", (amount, user_id, selected_wood))
                else:
                    c.execute("INSERT INTO user_inventory (discord_id, identity_id, item_key, item_name, item_count, item_image) VALUES (?, ?, ?, ?, ?, ?)",
                              (user_id, identity_id, selected_wood, selected_wood, amount, res_data["image"]))
                conn.commit()
                
                embed = discord.Embed(title="🪓 عملية تحطيب ناجحة", description=f"لقد قمت بتقطيع الأشجار وجمعت بعض الخشب!", color=discord.Color.dark_orange())
                embed.add_field(name="نوع الخشب", value=f"**{selected_wood}**", inline=True)
                embed.add_field(name="الكمية", value=f"`{amount}` قطعة", inline=True)
                embed.set_image(url=WOODCUTTING_IMAGE_URL)
                embed.set_thumbnail(url=res_data["image"])
                embed.set_footer(text="© Gold Town System | 2026")
                await inter.followup.send(embed=embed, ephemeral=True)
            else:
                await inter.response.send_message(f"✅ تم استخدام **{selected_item}** بنجاح!", ephemeral=True)
        
        async def give_callback(inter):
            class GiveItemModal(discord.ui.Modal, title='إعطاء غرض لشخص آخر'):
                target_id = discord.ui.TextInput(label='رقم هوية المستلم', placeholder='أدخل رقم الهوية هنا (مثال: 300123)...', min_length=6, max_length=6)
                give_qty = discord.ui.TextInput(label='الكمية', placeholder='أدخل العدد المراد إعطاؤه...', min_length=1, max_length=3)

                async def on_submit(self, modal_inter: discord.Interaction):
                    await modal_inter.response.defer(ephemeral=True)
                    try:
                        t_id = int(self.target_id.value)
                        g_qty = int(self.give_qty.value)
                        if g_qty <= 0: raise ValueError
                    except ValueError:
                        await modal_inter.followup.send("❌ يرجى إدخال بيانات صحيحة.", ephemeral=True)
                        return

                    # التحقق من توفر الكمية في شنطة المعطي
                    c.execute("SELECT item_count FROM user_inventory WHERE discord_id = ? AND item_name = ?", (user_id, selected_item))
                    current_row = c.fetchone()
                    if not current_row or current_row[0] < g_qty:
                        await modal_inter.followup.send("❌ ليس لديك هذه الكمية في شنطتك.", ephemeral=True)
                        return

                    # التحقق من وجود المستلم
                    c.execute("SELECT discord_id FROM players WHERE identity_id = ? LIMIT 1", (t_id,))
                    target_row = c.fetchone()
                    if not target_row:
                        await modal_inter.followup.send(f"❌ لم يتم العثور على شخصية تحمل رقم الهوية: `{t_id}`", ephemeral=True)
                        return
                    
                    target_discord_id = target_row[0]
                    if target_discord_id == user_id:
                        await modal_inter.followup.send("❌ لا يمكنك إعطاء أغراض لنفسك!", ephemeral=True)
                        return

                    # تنفيذ عملية النقل
                    # 1. خصم من المعطي
                    if current_row[0] == g_qty:
                        c.execute("DELETE FROM user_inventory WHERE discord_id = ? AND item_name = ?", (user_id, selected_item))
                    else:
                        c.execute("UPDATE user_inventory SET item_count = item_count - ? WHERE discord_id = ? AND item_name = ?", (g_qty, user_id, selected_item))
                    
                    # 2. إضافة للمستلم
                    c.execute("SELECT item_count FROM user_inventory WHERE discord_id = ? AND item_name = ?", (target_discord_id, selected_item))
                    target_inv = c.fetchone()
                    if target_inv:
                        c.execute("UPDATE user_inventory SET item_count = item_count + ? WHERE discord_id = ? AND item_name = ?", (g_qty, target_discord_id, selected_item))
                    else:
                        c.execute("INSERT INTO user_inventory (discord_id, identity_id, item_key, item_name, item_count, item_image) VALUES (?, ?, ?, ?, ?, ?)",
                                  (target_discord_id, t_id, selected_item, selected_item, g_qty, image))
                    
                    conn.commit()
                    await modal_inter.followup.send(f"✅ تم إعطاء **({g_qty}) {selected_item}** بنجاح لصاحب الهوية: `{t_id}`", ephemeral=True)
                    
                    # Send log to Inventory log channel
                    log_channel = bot.get_channel(INVENTORY_LOG_CHANNEL_ID)
                    if log_channel:
                        log_embed = discord.Embed(title="🎒 سجل نقل أغراض", color=discord.Color.blurple())
                        log_embed.add_field(name="من", value=interaction.user.mention, inline=True)
                        log_embed.add_field(name="إلى (هوية)", value=f"`{t_id}`", inline=True)
                        log_embed.add_field(name="الغرض", value=selected_item, inline=True)
                        log_embed.add_field(name="الكمية", value=f"`{g_qty}`", inline=True)
                        log_embed.set_footer(text=f"ID: {interaction.user.id}")
                        await log_channel.send(embed=log_embed)

                    # محاولة إرسال تنبيه للمستلم
                    try:
                        target_user = await bot.fetch_user(target_discord_id)
                        if target_user:
                            await target_user.send(f"🎒 **تنبيه شنطة:** لقد استلمت **({g_qty}) {selected_item}** من قبل {interaction.user.name}.")
                    except: pass

            await inter.response.send_modal(GiveItemModal())

        async def show_callback(inter):
            show_embed = discord.Embed(title=f"🎒 | عرض غرض", description=f"{interaction.user.mention} يعرض غرضاً من شنطته:\n**{selected_item}** (الكمية: {count})", color=discord.Color.gold())
            show_embed.set_thumbnail(url=image)
            show_embed.set_footer(text="© Gold Town System | 2026")
            await inter.channel.send(embed=show_embed)
            
            # Send log to Inventory log channel
            log_channel = bot.get_channel(INVENTORY_LOG_CHANNEL_ID)
            if log_channel:
                log_embed = discord.Embed(title="🎒 سجل عرض غرض", color=discord.Color.gold())
                log_embed.add_field(name="اللاعب", value=interaction.user.mention, inline=True)
                log_embed.add_field(name="الغرض", value=selected_item, inline=True)
                log_embed.add_field(name="الكمية المعروضة", value=f"`{count}`", inline=True)
                log_embed.set_footer(text=f"ID: {interaction.user.id}")
                await log_channel.send(embed=log_embed)

            await inter.response.send_message("✅ تم عرض الغرض بنجاح في القناة.", ephemeral=True)

        use_btn.callback = use_callback
        give_btn.callback = give_callback
        show_btn.callback = show_callback
        view.add_item(use_btn)
        view.add_item(give_btn)
        view.add_item(show_btn)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class InventoryView(discord.ui.View):
    def __init__(self, items):
        super().__init__(timeout=None)
        if items:
            self.add_item(InventoryItemSelect(items))
        else:
            self.add_item(discord.ui.Button(label="الشنطة فارغة", style=discord.ButtonStyle.secondary, disabled=True))

class MainBankView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # دائم لضمان عدم تعطل الأزرار أبداً

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
            await interaction.user.send(embed=embed_dm)
            
            embed_success = discord.Embed(title="✅ - Success", description="تم إنشاء حسابك بنجاح وإرسال تفاصيل الحساب إلى رسائلك الخاصة (DM)!", color=discord.Color.green())
            await interaction.followup.send(embed=embed_success, ephemeral=True)
        except Exception:
            embed_warn = discord.Embed(title="⚠️ - Warning", description="تم إنشاء حسابك بنجاح، ولكن تعذر إرسال الرسالة الخاصة تأكد من فتح رسائلك الخاصة (DM).", color=discord.Color.orange())
            await interaction.followup.send(embed=embed_warn, ephemeral=True)

@bot.command(name="trip")
async def trip_command(ctx):
    if not has_trip_permission(ctx.author):
        await ctx.send("عذراً، لا تمتلك رتبة `GT | Trip Support` أو صلاحية الأدمن لاستخدام هذا الأمر.", delete_after=5)
        return
    try:
        await ctx.message.delete()
    except Exception:
        pass
    
    class TripControlView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

        @discord.ui.button(label="فتح الرحلة", style=discord.ButtonStyle.success, emoji="🟢")
        async def open_trip(self, interaction: discord.Interaction, button: discord.ui.Button):
            global current_trip_status
            if not has_trip_permission(interaction.user):
                await interaction.response.send_message("❌ ليس لديك صلاحية للتحكم بالرحلة.", ephemeral=True)
                return
            current_trip_status = True
            
            c.execute("INSERT INTO trips (discord_id, status) VALUES (?, ?)", (interaction.user.id, "opened"))
            conn.commit()
            
            await interaction.response.send_message("🟢 **تم فتح الرحلة بنجاح!** يمكن الآن للاعبين تسجيل الدخول بشخصياتهم.", ephemeral=True)

        @discord.ui.button(label="إغلاق الرحلة", style=discord.ButtonStyle.danger, emoji="🔴")
        async def close_trip(self, interaction: discord.Interaction, button: discord.ui.Button):
            global current_trip_status
            if not has_trip_permission(interaction.user):
                await interaction.response.send_message("❌ ليس لديك صلاحية للتحكم بالرحلة.", ephemeral=True)
                return
            current_trip_status = False
            
            c.execute("INSERT INTO trips (discord_id, status) VALUES (?, ?)", (interaction.user.id, "closed"))
            conn.commit()
            
            await interaction.response.send_message("🔴 **تم إغلاق الرحلة بنجاح!**", ephemeral=True)

    await ctx.send("✈️ **لوحة التحكم السريعة للرحلة:**", view=TripControlView())

@bot.command(name="character")
async def character_command(ctx):
    if not await trip_check(ctx): return
    try:
        await ctx.message.delete()
    except Exception:
        pass
        
    embed = discord.Embed(title="Character Management", description="Character Creation, Login & Logout System", color=discord.Color.from_str("#111111"))
    embed.set_image(url=CHARACTER_SYSTEM_IMAGE)
    
    view = CharacterView()
    await ctx.send(embed=embed, view=view)

@bot.command(name="hospital")
async def hospital_command(ctx):
    if not await trip_check(ctx): return
    try:
        await ctx.message.delete()
    except Exception:
        pass

    embed = discord.Embed(
        title="🏥 | نظام المستشفى",
        description="اختر الخدمة التي تحتاجها في المستشفى.",
        color=discord.Color.from_str("#111111")
    )
    embed.set_image(url=HOSPITAL_IMAGE_URL)
    embed.set_footer(text="© Gold Town System | 2026")

    await ctx.send(embed=embed, view=HospitalView())

@bot.command(name="bank")
async def bank_command(ctx):
    if not await trip_check(ctx): return
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
            "يجب على كل عضو إنشاء حساب بنكي للاستفادة من الخدمات المالية وتحويل الأموال والإيداع والسحب بشكل آمن ومحفوظ."
        ),
        color=discord.Color.from_str("#111111")
    )
    embed.set_image(url=BANK_IMAGE_URL)
    embed.set_footer(text="© Effect Kings System | 2026")

    await ctx.send(embed=embed, view=MainBankView())

@bot.command(name="car_showroom")
async def car_showroom_command(ctx):
    if not await trip_check(ctx): return
    try:
        await ctx.message.delete()
    except Exception:
        pass

    embed = discord.Embed(
        title="🚗 | معرض السيارات",
        description="تصفح أحدث السيارات المتوفرة لدينا!",
        color=discord.Color.gold()
    )
    embed.set_image(url=CAR_SHOWROOM_IMAGE_URL)
    embed.set_footer(text="© Gold Town System | 2026")

    await ctx.send(embed=embed, view=CarShowroomView())

class TicketTypeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Support Ticket .", description="تكت دعم فني", emoji="🤝"),
            discord.SelectOption(label="Complaint Ticket .", description="تكت شكوى وحل مشكلات", emoji="⚠️"),
            discord.SelectOption(label="High Management Ticket .", description="تكت الإدارة العليا", emoji="👑"),
            discord.SelectOption(label="Add item Ticket .", description="تكت إضافة غرض", emoji="🎒"),
            discord.SelectOption(label="Owner Ticket .", description="تكت المالك", emoji="🔱")
        ]
        super().__init__(placeholder="اختر نوع التكت...", options=options)

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="Tickets")
        if not category:
            category = await guild.create_category("Tickets")
            
        ticket_type = self.values[0]
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        allowed_roles = []
        if "Support" in ticket_type:
            allowed_roles = ["GT | Support Team", "Technical Support"]
        elif "Complaint" in ticket_type:
            allowed_roles = ["GMS", "GT | High Tier 1", "GT | High Tier 2", "GT | High Tier 3", "GT | High Tier 4", "GT | High Tier 5", "GT | High Tier 6"]
        elif "High Management" in ticket_type:
            allowed_roles = ["GT | High Tier 1", "GT | High Tier 2", "GT | High Tier 3"]
        elif "Add item" in ticket_type:
            allowed_roles = ["Founder", "Co Founder", "Owner", "Co Owner"]
        elif "Owner" in ticket_type:
            allowed_roles = ["Owner", "Founder"]

        for role_name in allowed_roles:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        ticket_channel = await guild.create_text_channel(
            name=f"{ticket_type.split()[0].lower()}-{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )
        
        await interaction.response.send_message(f"✅ تم فتح التكت الخاص بك: {ticket_channel.mention}", ephemeral=True)
        
        embed = discord.Embed(
            title=f"📩 {ticket_type}",
            description=f"مرحباً {interaction.user.mention}، لقد فتحت تذكرة بخصوص **{ticket_type}**.\nيرجى شرح مشكلتك أو طلبك هنا وسيتم الرد عليك من قبل الفريق المختص قريباً.",
            color=discord.Color.blue()
        )
        embed.set_footer(text="© Gold Town System | 2026")
        await ticket_channel.send(embed=embed)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketTypeSelect())

@bot.command(name="tickets")
async def tickets_command(ctx):
    if not await trip_check(ctx): return
    embed = discord.Embed(
        title="📩 | Ticket System",
        description="الرجاء الضغط على الخيار في الأسفل لإظهار جميع أنواع التكتات.\n\nقم باختيار القسم الصحيح لفتح التذكرة.",
        color=discord.Color.teal()
    )
    embed.set_image(url=RULES_IMAGE_URL)
    embed.set_footer(text="© Gold Town System | 2026")
    await ctx.send(embed=embed, view=TicketView())

@bot.command(name="rules")
async def rules_command(ctx):
    embed = discord.Embed(
        title="📜 | قوانين سيرفر Gold Town",
        description="**هذه هي القوانين الرسمية لسيرفر Gold Town، يرجى قراءتها والالتزام بها.**\n\n**قوانين المجتمع:**\n1. **لا عقلية الفوز فقط**: اللعب التنافسي ضروري للعب الأدوار الناجح.\n2. **لعب الأدوار قبل إراقة الدماء**: لا يوجد قتل عشوائي (RDM) أو قتل عند الرؤية (KOS). يجب أن يبدأ أي نزاع شفهياً أو بقصة طويلة تؤدي إلى النزاع ضمن مسافة قريبة. يجب أن يكون هدف الهجوم قادراً على التعرف على أنه مهدد بالضرر، ولماذا، ومن قبل من قبل أن يصاب.\n3. **الميتاجيمنج ممنوع**: لا تتصرف بناءً على معلومات لم يكتسبها شخصيتك داخل السيرفر.\n4. **الباور جيمنج ممنوع**: لعب الأدوار الذي لا يمنح اللاعبين الآخرين فرصة للعب أدوار شخصياتهم الخاصة يعتبر باور جيمنج.\n5. **الستريم سنايبنج ممنوع**.\n6. لعب الأدوار الذي ينتهك شروط خدمة Twitch وإرشادات مجتمع Twitch ممنوع.\n7. يجب أن يكون اللاعبون وشخصياتهم **18 عاماً أو أكبر**.\n8. يجب أن يتمتع اللاعبون **بطلاقة في اللغة الإنجليزية** بما يكفي للفهم والتفاهم بسهولة.\n9. يجب ربط حساب Steam الخاص بك بـ Discord الخاص بك.\n10. يجب إعطاء الأولوية لإجراءات الإدارة عبر Discord.\n11. كن محترماً للاعبين الآخرين في المجتمع؛ الإهانات أو الهجمات الشخصية خارج لعب الأدوار ممنوعة تماماً.\n12. **التواصل الصوتي**:\n    - يجب أن يكون لدى اللاعبين ميكروفون وسماعة رأس بجودة جيدة وعاملة للعب الأدوار الصوتي.\n    - يجب عدم استخدام الاتصال الخارجي للتواصل مع لاعبين آخرين أثناء وجودك في السيرفر.\n13. استخدم الأدوات والقنوات المناسبة للإبلاغ عن المشكلات أو طلب الدعم.\n14. **استغلال الأخطاء (Glitching/Exploiting) ممنوع**.\n15. يجب أن يكون اللاعبون **في شخصيتهم** في جميع الأوقات داخل السيرفر. وهذا يشمل التواصل والإجراءات.\n16. **قيود المحتوى**:\n    - **العنف الشديد**: يجب الحصول على موافقة OOC عبر Discord بين جميع الأطراف قبل لعب أدوار التعذيب/التشويه.\n    - **المواضيع المحظورة**: لعب الأدوار والإشارات إلى المواضيع التالية، شفهياً وكتابياً، غير مسموح بها إطلاقاً وقد يؤدي إلى حظر دائم: العنصرية أو التمييز الجنسي، الانتحار أو إيذاء النفس، لعب أدوار الأطفال/الحمل، لعب الأدوار الجنسي (ERP)، لعب أدوار العبودية، خطاب الكراهية أو الإهانات أو تصوير جرائم الكراهية.\n17. **قوانين Discord**:\n    - يجب عليك اتباع شروط خدمة Discord.\n    - الإعلان من أي نوع لن يتم التسامح معه إلا بإذن صريح من الإدارة.\n    - لا ترسل رسائل سبام للبوت.\n    - الأسماء والصور الرمزية المسيئة/غير اللائقة غير مسموح بها.\n    - للإدارة الكلمة الأخيرة فيما هو مسموح به.\n\n**قوانين السيرفر:**\n1. يجب أن تقدر حياتك وحريتك وحياة الآخرين.\n2. لا تكتب قصصاً. لا بأس في إعداد خطوط قصة فضفاضة في بداية القصة، ولكن محاولة التحكم في السرد تتعارض مع قوانين السيرفر. هذا السيرفر يدور حول سرد القصص التعاوني.\n3. المجموعات أو العائلات أو الشركات (المدنية أو الإجرامية) محدودة بـ 16 شخصاً كحد أقصى.\n4. يجب الموافقة على أي مجموعات أو شخصيات LORE من خلال اتفاقية مجموعة فائقة.\n5. لا يُسمح لك بلعب دور قاتل متسلسل بدون اتفاقية قاتل متسلسل.\n6. أرقام القتال هي كما يلي:\n    - 6 ضد 6 لصراع العصابات.\n    - 6 ضد 7 لصراع العصابات والشرطة، يُسمح للعصابات بـ 6 بينما يُسمح للشرطة بـ 7.\n    - إذا اضطرت الشرطة للتدخل في صراع 6 ضد 6 للعصابات، يُسمح لهم بـ 8. بفعالية 6 لعصابة واحدة مقابل 6 لعصابة أخرى مقابل 8 ضباط شرطة.\n7. **قاعدة الحياة الجديدة (NEW LIFE RULE)**:\n    - إذا قمت بالضغط على E لإعادة الظهور أو انتهى المؤقت وأعدت الظهور في المستشفى؛ فأنت لا تتذكر أي شيء أدى إلى وفاتك.\n    - إذا كنت عاجزاً (بمعنى - ترى النص لطلب سيارة إسعاف أو تضغط على E لإعادة الظهور) يجب ألا تتذكر أي شيء من لحظة عجزك حتى يتم إنعاشك.\n8. لإعادة شخصية ماتت بشكل دائم، يجب عليك البحث عن اتفاق مع فريق الإدارة.\n9. السرقات محدودة بـ 4 و 6 مجرمين كحد أقصى. وهي كالتالي:\n    - 4 مجرمين كحد أقصى: بنك فليكا، المتاجر، ورشة التقطيع، صفقات المخدرات، الاحتيال، سرقات المنازل من NPC.\n    - 6 مجرمين كحد أقصى: بنك ميز، باسيفيك ستاندرد، شاحنة البنك، لايف إنفيدر.",
        color=discord.Color.dark_blue()
    )
    embed.set_image(url=RULES_IMAGE_URL)
    embed.set_footer(text="© Gold Town System | 2026")
    await ctx.send(embed=embed)

@bot.command(name="start_trip")
@commands.has_permissions(administrator=True)
async def start_trip(ctx):
    c.execute("UPDATE server_config SET value = 'true' WHERE key = 'trip_active'")
    conn.commit()
    await ctx.send("✅ تم بدء الرحلة بنجاح! جميع الأنظمة متاحة الآن.")

@bot.command(name="end_trip")
@commands.has_permissions(administrator=True)
async def end_trip(ctx):
    c.execute("UPDATE server_config SET value = 'false' WHERE key = 'trip_active'")
    conn.commit()
    await ctx.send("🛑 تم إنهاء الرحلة. تم إيقاف الأنظمة مؤقتاً.")

@bot.command(name="ikea")
async def ikea_command(ctx):
    if not await trip_check(ctx): return
    try:
        await ctx.message.delete()
    except Exception:
        pass

    embed = discord.Embed(
        title="🛒 | متجر ايكيا للأدوات",
        description="تجد هنا كافة الأدوات الأساسية التي تحتاجها في حياتك اليومية.",
        color=discord.Color.gold()
    )
    embed.set_image(url=IKEA_IMAGE_URL)
    embed.set_footer(text="© Gold Town System | 2026")

    await ctx.send(embed=embed, view=IkeaStoreView())

@bot.command(name="mine", aliases=["منجم"])
async def mine_command(ctx):
    if not await trip_check(ctx): return
    user_id = ctx.author.id
    c.execute("SELECT item_name, item_count FROM user_inventory WHERE discord_id = ?", (user_id,))
    items = c.fetchall()
    
    embed = discord.Embed(
        title="⛏️ | منجم Gold Town",
        description="أهلاً بك في المنجم. يمكنك هنا بيع الموارد التي جمعتها.\n💡 **ملاحظة:** للتعدين، استخدم الفأس من شنطتك.",
        color=discord.Color.dark_gray()
    )
    embed.set_image(url=MINING_IMAGE_URL)
    embed.set_footer(text="© Gold Town System | 2026")
    
    await ctx.send(embed=embed, view=MiningView(items))

@bot.command(name="سرقة", aliases=["rob", "heist"])
async def heist_command(ctx):
    if not await trip_check(ctx): return
    user_id = ctx.author.id
    c.execute("SELECT heist_progress, identity_id FROM players WHERE discord_id = ?", (user_id,))
    row = c.fetchone()
    if not row:
        await ctx.send("❌ يجب أن يكون لديك شخصية مسجلة للبدء.")
        return
    
    progress, identity_id = row
    
    embed = discord.Embed(title="🕵️ | قائمة السرقات المتاحة", description="اختر الهدف الذي تريد سرقته. تذكر: الفشل قد يبلغ الشرطة!", color=discord.Color.red())
    embed.set_image(url=HEIST_IMAGE_URL)
    
    view = discord.ui.View()
    
    for name, config in HEIST_CONFIG.items():
        is_locked = progress < config["progress_needed"]
        btn_style = discord.ButtonStyle.gray if is_locked else discord.ButtonStyle.danger
        label = f"سرقة {name} {'🔒' if is_locked else ''}"
        
        async def make_callback(n=name, conf=config):
            async def callback(inter: discord.Interaction):
                # التحقق من المتطلب في الشنطة
                c.execute("SELECT item_count FROM user_inventory WHERE discord_id = ? AND item_name = ?", (user_id, conf["requirement"]))
                inv_row = c.fetchone()
                if not inv_row or inv_row[0] <= 0:
                    await inter.response.send_message(f"❌ تحتاج إلى **{conf['requirement']}** للقيام بهذه السرقة!", ephemeral=True)
                    return
                
                # إنشاء لغز عشوائي بناءً على الصعوبة
                diff = conf["difficulty"]
                num1 = random.randint(10*diff, 50*diff)
                num2 = random.randint(5*diff, 20*diff)
                correct_answer = num1 + num2
                
                class HeistPuzzleModal(discord.ui.Modal, title=f'فك شفرة {n}'):
                    answer = discord.ui.TextInput(label=f'حل اللغز: {num1} + {num2} = ؟', placeholder='أدخل الإجابة بسرعة...', min_length=1, max_length=5)

                    async def on_submit(self, modal_inter: discord.Interaction):
                        try:
                            user_ans = int(self.answer.value)
                        except: user_ans = -1
                        
                        if user_ans == correct_answer:
                            # نجاح السرقة
                            reward = random.randint(conf["min_reward"], conf["max_reward"])
                            new_progress = max(progress, conf["progress_needed"] + 1)
                            c.execute("UPDATE players SET balance = balance + ?, heist_progress = ? WHERE discord_id = ?", 
                                      (reward, new_progress, user_id))
                            
                            key_msg = ""
                            if "key_reward" in conf:
                                c.execute("SELECT item_count FROM user_inventory WHERE discord_id = ? AND item_name = ?", (user_id, conf["key_reward"]))
                                if not c.fetchone():
                                    c.execute("INSERT INTO user_inventory (discord_id, identity_id, item_key, item_name, item_count, item_image) VALUES (?, ?, ?, ?, ?, ?)",
                                              (user_id, identity_id, conf["key_reward"], conf["key_reward"], 1, "https://i.postimg.cc/m2j8zW4P/key-icon.png"))
                                    key_msg = f"\n🔑 ولقد حصلت على: **{conf['key_reward']}**"
                            
                            conn.commit()
                            await modal_inter.response.send_message(f"✅ تمت السرقة بنجاح! حصلت على **{reward:,} $** {key_msg}", ephemeral=True)
                        else:
                            # فشل السرقة وبلاغ للشرطة
                            await modal_inter.response.send_message("❌ أخطأت في اللغز! لقد انطلق إنذار الشرطة!", ephemeral=True)
                            police_channel = bot.get_channel(POLICE_LOG_CHANNEL_ID)
                            if police_channel:
                                p_embed = discord.Embed(title="🚨 بلاغ سرقة عاجل", description=f"تم رصد محاولة سرقة فاشلة في **{conf['location']}**!", color=discord.Color.red())
                                p_embed.add_field(name="الموقع الدقيق", value=conf['location'], inline=True)
                                p_embed.add_field(name="المشتبه به", value=inter.user.mention, inline=True)
                                p_embed.add_field(name="الحالة", value="⚠️ تم تفعيل إنذار السرقة!", inline=False)
                                p_embed.set_image(url=conf['rob_image'])
                                p_embed.set_footer(text=f"ID: {interaction.user.id} | © Gold Town Police")
                                await police_channel.send(content=f"@here 🚔 **انتباه لجميع الوحدات!**", embed=p_embed)
                
                await inter.response.send_modal(HeistPuzzleModal())
            return callback

        btn = discord.ui.Button(label=label, style=btn_style, disabled=is_locked)
        btn.callback = await make_callback(name, config)
        view.add_item(btn)
        
    await ctx.send(embed=embed, view=view)

@bot.command(name="شنطة", aliases=["bag", "inv"])
async def inventory_command(ctx):
    if not await trip_check(ctx): return
    user_id = ctx.author.id
    c.execute("SELECT item_name, item_count FROM user_inventory WHERE discord_id = ?", (user_id,))
    items = c.fetchall()
    
    embed = discord.Embed(
        title="🎒 | شنطة الشخصية",
        description="هنا تجد جميع الأغراض والأدوات التي تحملها معك.",
        color=discord.Color.gold()
    )
    embed.set_thumbnail(url=CHARACTER_SYSTEM_IMAGE)
    
    if not items:
        embed.add_field(name="الحالة", value="الشنطة فارغة حالياً.")
    else:
        item_list = "\n".join([f"🔹 **{item[0]}** | العدد: `{item[1]}`" for item in items])
        embed.add_field(name="الأغراض", value=item_list)
        
    embed.set_footer(text="© Gold Town System | 2026")
    await ctx.send(embed=embed, view=InventoryView(items))

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
 
