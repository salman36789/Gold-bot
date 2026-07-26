import discord
from discord.ext import commands
import sqlite3
import os
import random
import asyncio
import re

DB_FILE = 'bot_database.db'

conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                discord_id INTEGER, 
                identity_id INTEGER UNIQUE,
                psn_id TEXT,
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
TARGET_VERIFY_CHANNEL_ID = 1530770263598301225

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    
    # ضبط الصلاحيات تلقائياً لكل السيرفر فور تشغيل البوت
    for guild in bot.guilds:
        await setup_server_permissions(guild)
        
    print("تم ضبط كافة الأقسام والصلاحيات تلقائياً بنجاح!")

async def setup_server_permissions(guild):
    inactive_role = discord.utils.get(guild.roles, name="Inactive")
    identity_role = discord.utils.get(guild.roles, name="Identity")
    
    game_categories_names = [
        "gt | on display", "gt | theft", "collection", "gt | justice team", 
        "gt | phone", "gt | command", "gold town public", "social"
    ]
    
    for cat in guild.categories:
        cat_name_lower = cat.name.lower()
        
        # 1. قسم الأقيام أو الجيم: إغلاق الكتابة للجميع عدا الإدارة
        if "game" in cat_name_lower or "أقيام" in cat_name_lower or "اقيام" in cat_name_lower:
            await cat.set_permissions(guild.default_role, send_messages=False)
            if identity_role:
                await cat.set_permissions(identity_role, send_messages=False)
                
        # 2. أقسام الـ RP: إخفاء عن Inactive، وجعلها مشاهدة فقط (قراءة) لمن لديه Identity
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
        print(f"خطأ عند دخول العضو: {e}")

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
            print(f"خطأ في التفعيل التلقائي: {e}")

    await bot.process_commands(message)

def is_valid_psn_id(psn_id):
    pattern = r'^[a-zA-Z][a-zA-Z0-9_-]{2,15}$'
    return bool(re.match(pattern, psn_id))

class RegistrationModal(discord.ui.Modal, title='إنشاء شخصية جديدة بربط سوني'):
    psn_id = discord.ui.TextInput(label='أيدي السوني (PSN ID)', placeholder='مثال: Ahmed_KSA...', min_length=3, max_length=16)
    birthdate = discord.ui.TextInput(label='مواليد الشخصية', placeholder='مثال: 1998/05/12')
    birthplace = discord.ui.TextInput(label='مكان الولادة', placeholder='أدخل مكان الولادة...')
    bio = discord.ui.TextInput(label='فكرة الشخصية', style=discord.TextStyle.paragraph, placeholder='اكتب قصة شخصيتك هنا...')

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        guild = interaction.guild
        member = interaction.user
        entered_psn = self.psn_id.value.strip()

        if not is_valid_psn_id(entered_psn):
            await interaction.response.send_message(
                "❌ **أيدي سوني (PSN ID) غير صحيح!**\n"
                "يجب أن يتكون من 3 إلى 16 حرفاً، يبدأ بحرف إنجليزي، ولا يحتوي على مسافات أو رموز غريبة (مسموح بالشرطة السفلية `_` والشرطة `-`).",
                ephemeral=True
            )
            return
        
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

        character_name = entered_psn

        c.execute("INSERT INTO players (discord_id, identity_id, psn_id, birthdate, birthplace, bio, balance, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                  (user_id, new_identity, entered_psn, self.birthdate.value, self.birthplace.value, self.bio.value, 1000, 'active'))
        conn.commit()
        
        try:
            try:
                await member.edit(nick=character_name)
            except Exception as nick_err:
                print(f"ملاحظة: لم يتمكن البوت من تغيير النيك نيم: {nick_err}")

            inactive_role = discord.utils.get(guild.roles, name="Inactive")
            identity_role = discord.utils.get(guild.roles, name="Identity")
            
            if inactive_role and inactive_role in member.roles:
                await member.remove_roles(inactive_role)
            
            if identity_role and identity_role not in member.roles:
                await member.add_roles(identity_role)

            blue_role = await guild.create_role(name=character_name, color=discord.Color.blue(), reason="رتبة هوية اللاعب برابط سوني")
            await member.add_roles(blue_role)
            
            verified_role = discord.utils.get(guild.roles, name="Verified")
            unverified_role = discord.utils.get(guild.roles, name="Unverified")
            if verified_role:
                await member.add_roles(verified_role)
            if unverified_role and unverified_role in member.roles:
                await member.remove_roles(unverified_role)

            # تطبيق الصلاحيات بشكل فوري على الأقسام فور إنشاء الشخصية
            await setup_server_permissions(guild)

        except Exception as e:
            print(f"خطأ في إعدادات الرتب والصلاحيات: {e}")

        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(
                f"📇 **تم إنشاء شخصية جديدة بنجاح:** {interaction.user.mention}\n"
                f"🎮 **أيدي سوني:** `{entered_psn}`\n"
                f"🆔 **رقم الهوية:** `{new_identity}`\n"
                f"👤 **الاسم الجديد:** {character_name}\n"
                f"📅 **المواليد:** {self.birthdate.value}"
            )
            
        await interaction.response.send_message(f"✅ تم إنشاء شخصيتك بنجاح! وتحديث صلاحيات الأقسام تلقائياً.", ephemeral=True)

class CharacterSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Create Character", description="لإنشاء شخصية جديدة بربط سوني (بحد أقصى 3)"),
            discord.SelectOption(label="Show identity", description="لعرض الهويات المسجلة وأيديات السوني")
        ]
        super().__init__(placeholder="Choose an action you want to make", options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        if self.values[0] == "Create Character":
            await interaction.response.send_modal(RegistrationModal())
        elif self.values[0] == "Show identity":
            c.execute("SELECT identity_id, psn_id, birthdate, birthplace, balance FROM players WHERE discord_id = ?", (user_id,))
            players = c.fetchall()
            if players:
                text = "هوياتك المسجلة:\n"
                for idx, p in enumerate(players, 1):
                    text += f"\n**الشخصية {idx}:**\n- 🆔 رقم الهوية: `{p[0]}`\n- 🎮 أيدي سوني: `{p[1]}`\n- 📅 المواليد: `{p[2]}`\n- 💰 الرصيد: `{p[4]}`\n"
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

