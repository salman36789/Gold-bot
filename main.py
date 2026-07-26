import discord
from discord.ext import commands
import sqlite3
import os
import random
import asyncio
import re
from datetime import datetime

DB_FILE = 'bot_database.db'

conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                discord_id INTEGER, 
                identity_id INTEGER UNIQUE,
                first_name TEXT,
                last_name TEXT,
                mind TEXT,
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

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

LOG_CHANNEL_ID = 1530791985131032656
TARGET_VERIFY_CHANNEL_ID = 1530770263598301225
IMAGE_URL = "https://cdn.discordapp.com/attachments/1530705141710327868/1530710244332929034/Screenshot_20260726_012651.jpg"

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    for guild in bot.guilds:
        await setup_server_permissions(guild)
    print("Bot is online and running successfully!")

async def setup_server_permissions(guild):
    inactive_role = discord.utils.get(guild.roles, name="Inactive")
    identity_role = discord.utils.get(guild.roles, name="Identity")
    
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

def validate_character_data(first_name, last_name, birthdate_str, birthplace):
    if re.search(r'[\u0600-\u06FF]', first_name) or re.search(r'[\u0600-\u06FF]', last_name):
        return False, "❌ تم الرفض: ممنوع كتابة الاسم باللغة العربية (يجب أن يكون بالإنجليزية)."
    
    if ' ' in first_name.strip():
        return False, "❌ تم الرفض: الاسم الأول يحتوي على مسافات، يجب أن يكون اسماً واحداً."
    if ' ' in last_name.strip():
        return False, "❌ تم الرفض: الاسم الثاني يحتوي على مسافات، يجب أن يكون اسماً واحداً."

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

    allowed_birthplaces = ["بوليتو", "ساندي", "لوس"]
    clean_birthplace = birthplace.strip()
    if clean_birthplace not in allowed_birthplaces:
        return False, "❌ تم الرفض: مكان الولادة غير مسموح به. الأماكن المسموحة فقط هي: (بوليتو، ساندي، لوس)."

    return True, "تم بنجاح"

class RegistrationModal(discord.ui.Modal, title='إنشاء شخصية جديدة'):
    first_name = discord.ui.TextInput(label='الاسم الأول (اسم واحد إنجليزي بدون مسافات)', placeholder='مثال: John...')
    last_name = discord.ui.TextInput(label='الاسم الثاني (اسم واحد إنجليزي بدون مسافات)', placeholder='مثال: Wick...')
    birthdate = discord.ui.TextInput(label='مواليد الشخصية (يوم/شهر/سنة)', placeholder='مثال: 1/1/1999')
    birthplace = discord.ui.TextInput(label='مكان الولادة (بوليتو / ساندي / لوس)', placeholder='أدخل مكان الولادة...')
    mind = discord.ui.TextInput(label='فكر الشخصية', placeholder='أدخل فكر الشخصية...')

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        guild = interaction.guild
        member = interaction.user
        
        f_name = self.first_name.value.strip()
        l_name = self.last_name.value.strip()
        entered_birth = self.birthdate.value.strip()
        entered_place = self.birthplace.value.strip()
        entered_mind = self.mind.value.strip()

        is_valid, message_result = validate_character_data(f_name, l_name, entered_birth, entered_place)
        if not is_valid:
            # إرسال سبب الرفض في الخاص (DM)
            try:
                await member.send(f"❌ **عذراً، تم رفض طلب إنشاء شخصيتك.**\n**السبب:** {message_result}")
            except Exception:
                pass
            await interaction.response.send_message(message_result, ephemeral=True)
            return
        
        c.execute("SELECT COUNT(*) FROM players WHERE discord_id = ?", (user_id,))
        count = c.fetchone()[0]
        
        if count >= 3:
            error_msg = "❌ عذراً، لا يمكنك امتلاك أكثر من 3 شخصيات نشطة!"
            try:
                await member.send(f"❌ **عذراً، تم رفض طلب إنشاء شخصيتك.**\n**السبب:** {error_msg}")
            except Exception:
                pass
            await interaction.response.send_message(error_msg, ephemeral=True)
            return

        while True:
            new_identity = random.randint(300000, 399999)
            c.execute("SELECT 1 FROM players WHERE identity_id = ?", (new_identity,))
            if not c.fetchone():
                break

        role_character_name = f"{f_name} {l_name}"

        c.execute("INSERT INTO players (discord_id, identity_id, first_name, last_name, mind, birthdate, birthplace, bio, balance, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                  (user_id, new_identity, f_name, l_name, entered_mind, entered_birth, entered_place, "مقبول تلقائياً", 1000, 'active'))
        conn.commit()
        
        try:
            try:
                await member.edit(nick=role_character_name)
            except Exception as nick_err:
                print(f"Note: Nickname error: {nick_err}")

            inactive_role = discord.utils.get(guild.roles, name="Inactive")
            identity_role = discord.utils.get(guild.roles, name="Identity")
            
            if inactive_role and inactive_role in member.roles:
                await member.remove_roles(inactive_role)
            
            if identity_role and identity_role not in member.roles:
                await member.add_roles(identity_role)

            blue_role = await guild.create_role(name=role_character_name, color=discord.Color.blue(), reason="رتبة اسم الشخصية")
            await member.add_roles(blue_role)
            
            verified_role = discord.utils.get(guild.roles, name="Verified")
            unverified_role = discord.utils.get(guild.roles, name="Unverified")
            if verified_role:
                await member.add_roles(verified_role)
            if unverified_role and unverified_role in member.roles:
                await member.remove_roles(unverified_role)

            await setup_server_permissions(guild)

        except Exception as e:
            print(f"Error in roles/permissions: {e}")

        # إرسال رسالة القبول والهوية في الخاص (DM) لصاحب الشخصية
        try:
            await member.send(
                f"🎉 **مبروك! تم قبول شخصيتك بنجاح.**\n"
                f"👤 **اسم الشخصية:** `{role_character_name}`\n"
                f"🆔 **رقم الهوية:** `{new_identity}`\n"
                f"🧠 **فكر الشخصية:** `{entered_mind}`\n"
                f"📅 **المواليد:** `{entered_birth}`\n"
                f"📍 **مكان الولادة:** `{entered_place}`"
            )
        except Exception:
            pass

        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(
                f"🎉 **تم قبول وإنشاء شخصية جديدة تلقائياً:** {interaction.user.mention}\n"
                f"👤 **اسم الشخصية (الرول):** `{role_character_name}`\n"
                f"🧠 **فكر الشخصية:** `{entered_mind}`\n"
                f"🆔 **رقم الهوية:** `{new_identity}`\n"
                f"📅 **المواليد:** `{entered_birth}`\n"
                f"📍 **مكان الولادة:** `{entered_place}`"
            )
            
        await interaction.response.send_message(f"✅ مبروك! اجتازت شخصيتك كافة الشروط وتم **قبولها تلقائياً** وإرسال تفاصيل الهوية إلى رسائلك الخاصة (DM).", ephemeral=True)

class ForgeModal(discord.ui.Modal, title='تزوير هوية شخصية'):
    first_name = discord.ui.TextInput(label='الاسم الأول الجديد (إنجليزي)', placeholder='مثال: John...')
    last_name = discord.ui.TextInput(label='الاسم الثاني الجديد (إنجليزي)', placeholder='مثال: Wick...')
    birthdate = discord.ui.TextInput(label='مواليد الشخصية الجديدة (يوم/شهر/سنة)', placeholder='مثال: 1/1/1999')
    birthplace = discord.ui.TextInput(label='مكان الولادة (بوليتو / ساندي / لوس)', placeholder='أدخل مكان الولادة...')

    def __init__(self, identity_id, old_full_name):
        super().__init__()
        self.identity_id = identity_id
        self.old_full_name = old_full_name

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        guild = interaction.guild
        member = interaction.user
        
        f_name = self.first_name.value.strip()
        l_name = self.last_name.value.strip()
        entered_birth = self.birthdate.value.strip()
        entered_place = self.birthplace.value.strip()

        is_valid, message_result = validate_character_data(f_name, l_name, entered_birth, entered_place)
        if not is_valid:
            try:
                await member.send(f"❌ **عذراً، فشلت عملية تزوير الهوية.**\n**السبب:** {message_result}")
            except Exception:
                pass
            await interaction.response.send_message(message_result, ephemeral=True)
            return

        new_full_name = f"{f_name} {l_name}"

        c.execute("""UPDATE players 
                     SET first_name = ?, last_name = ?, birthdate = ?, birthplace = ? 
                     WHERE identity_id = ? AND discord_id = ?""",
                  (f_name, l_name, entered_birth, entered_place, self.identity_id, user_id))
        conn.commit()

        try:
            try:
                await member.edit(nick=new_full_name)
            except Exception as e:
                print(f"Nickname note: {e}")

            old_role = discord.utils.get(guild.roles, name=self.old_full_name)
            if old_role:
                await old_role.delete(reason="تزوير هوية وتغيير اسم الشخصية")

            new_role = await guild.create_role(name=new_full_name, color=discord.Color.blue(), reason="رتبة تزوير الهوية الجديدة")
            await member.add_roles(new_role)

        except Exception as e:
            print(f"Error in forge role edit: {e}")

        try:
            await member.send(f"⚠️ **تم تزوير وتحديث هويتك بنجاح!**\n🆔 رقم الهوية: `{self.identity_id}`\n👤 الاسم الجديد: `{new_full_name}`")
        except Exception:
            pass

        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(
                f"⚠️ **تم تزوير وتحديث هوية بنجاح:** {interaction.user.mention}\n"
                f"👤 **الاسم القديم:** `{self.old_full_name}` ➡️ **الاسم المزور الجديد:** `{new_full_name}`\n"
                f"🆔 **رقم الهوية:** `{self.identity_id}`"
            )

        await interaction.response.send_message(f"✅ نجحت عملية التزوير! تم تحديث هويتك واسمك إلى: `{new_full_name}`.", ephemeral=True)

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
        guild = interaction.guild
        member = interaction.user

        try:
            await member.edit(nick=char_name)
            new_role = discord.utils.get(guild.roles, name=char_name)
            if not new_role:
                new_role = await guild.create_role(name=char_name, color=discord.Color.blue())
            
            await member.add_roles(new_role)
            await interaction.response.send_message(f"✅ تم تسجيل الدخول بالشخصية بنجاح: `{char_name}` وتحديث رتبتك ونيك نيم السيرفر!", ephemeral=True)
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
        guild = interaction.guild
        member = interaction.user

        try:
            role_to_remove = discord.utils.get(guild.roles, name=char_name)
            if role_to_remove and role_to_remove in member.roles:
                await member.remove_roles(role_to_remove)
            
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
        elif self.values[0] == "Login":
            c.execute("SELECT identity_id, first_name, last_name FROM players WHERE discord_id = ?", (user_id,))
            players = c.fetchall()
            if players:
                await interaction.response.send_message("اختر الشخصية لتسجيل الدخول:", view=LoginSelectView(players), ephemeral=True)
            else:
                await interaction.response.send_message("❌ ليس لديك أي شخصيات مسجلة لتسجيل الدخول بها!", ephemeral=True)
        elif self.values[0] == "Logout":
            c.execute("SELECT identity_id, first_name, last_name FROM players WHERE discord_id = ?", (user_id,))
            players = c.fetchall()
            if players:
                await interaction.response.send_message("اختر الشخصية لتسجيل الخروج منها:", view=LogoutSelectView(players), ephemeral=True)
            else:
                await interaction.response.send_message("❌ ليس لديك شخصيات مسجلة!", ephemeral=True)
        elif self.values[0] == "Show identity":
            c.execute("SELECT identity_id, first_name, last_name, mind, birthdate, birthplace, balance FROM players WHERE discord_id = ?", (user_id,))
            players = c.fetchall()
            if players:
                text = "هوياتك المسجلة:\n"
                for idx, p in enumerate(players, 1):
                    text += f"\n**الشخصية {idx}:**\n- 👤 الاسم: `{p[1]} {p[2]}`\n- 🆔 رقم الهوية: `{p[0]}`\n- 🧠 فكر الشخصية: `{p[3]}`\n- 📅 المواليد: `{p[4]}`\n- 📍 مكان الولادة: `{p[5]}`\n- 💰 الرصيد: `{p[6]}`\n"
                await interaction.response.send_message(text, ephemeral=True)
            else:
                await interaction.response.send_message("❌ ليس لديك أي شخصيات مسجلة!", ephemeral=True)

class CharacterView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(CharacterSelect())

class ForgeButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="تزوير هوية", style=discord.ButtonStyle.danger, custom_id="forge_identity_button")
    async def forge_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        c.execute("SELECT identity_id, first_name, last_name FROM players WHERE discord_id = ?", (user_id,))
        players = c.fetchall()
        if players:
            await interaction.response.send_message("اختر الشخصية التي تريد تزوير بياناتها من القائمة أدناه:", view=ForgeSelectView(players), ephemeral=True)
        else:
            await interaction.response.send_message("❌ ليس لديك أي شخصيات مسجلة لتزويرها!", ephemeral=True)

@bot.command(name="character")
async def character_command(ctx):
    embed = discord.Embed(title="Character Management", description="Character Creation, Login & Logout System", color=discord.Color.gold())
    embed.set_image(url=IMAGE_URL)
    await ctx.send(embed=embed, view=CharacterView())

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
    if ctx.author != ctx.guild.owner and not ctx.author.guild_permissions.administrator:
        return
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 تم حذف {amount} رسالة بنجاح.")
    await asyncio.sleep(3)
    try:
        await msg.delete()
    except:
        pass

bot.run(os.getenv('TOKEN'))
 
