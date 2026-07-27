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
                balance INTEGER DEFAULT 1000, 
                status TEXT
            )''')

c.execute('''CREATE TABLE IF NOT EXISTS trips (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             discord_id INTEGER,
             status TEXT
          )''')

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
TARGET_ACTION_ROOM_ID = 1530770304056557751  
BANK_LOG_CHANNEL_ID = 1531305086666412163  
REQUIRED_ROLE_NAME = "GT | Trip Support"

BLACK_IMAGE_URL = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1000&auto=format&fit=crop"
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
            await interaction.response.send_message(f"🟡 تم تسجيل الخروج من الشخصية: `{char_name}` بنجاح مع حفظ كافة بياناتها وأغراضها.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ حدث خطأ أثناء تسجيل الخروج: {e}", ephemeral=True)

class LogoutSelectView(discord.ui.View):
    def __init__(self, players):
        super().__init__()
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
                text = "هوياتك المسجلة والمحفوظة:\n"
                for idx, p in enumerate(players, 1):
                    text += f"\n**الشخصية {idx}:**\n- 👤 الاسم: `{p[1]} {p[2]}`\n- 🆔 رقم الهوية: `{p[0]}`\n- 📅 المواليد: `{p[3]}`\n- ⚧️ الجنس: `{p[4]}`\n- 📍 مكان الولادة: `{p[5]}`\n- 💰 الكاش: `{p[6]} $`\n"
                await interaction.followup.send(text, ephemeral=True)
            else:
                await interaction.followup.send("❌ ليس لديك أي شخصيات مسجلة!", ephemeral=True)

class CharacterView(discord.ui.View):
    def __init__(self, timeout=None):
        super().__init__(timeout=timeout)

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
            
            embed_success = discord.Embed(title="✅ - Success", description="تم إنشاء حسابك البنكي وإرسال تفاصيل الحساب إلى رسائلك الخاصة (DM)!", color=discord.Color.green())
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
    await ctx.send("✈️ **لوحة التحكم السريعة للرحلة:**")

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
            "يجب على كل عضو إنشاء حساب بنكي للاستفادة من الخدمات المالية وتحويل الأموال والإيداع والسحب بشكل آمن ومحفوظ."
        ),
        color=discord.Color.from_str("#111111")
    )
    embed.set_image(url=BANK_IMAGE_URL)
    embed.set_footer(text="© Effect Kings System | 2026")

    await ctx.send(embed=embed, view=MainBankView())

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
 
