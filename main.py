import discord
from discord.ext import commands
import sqlite3
import os
import random
import asyncio

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
TARGET_VERIFY_CHANNEL_ID = 1530770263598301225 # روم الأيدي المحدد

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    print("البوت يعمل بنجاح ومبرمج على روم التفعيل المحدد!")

# إعطاء رتبة Unverified تلقائياً عند دخول أي عضو جديد
@bot.event
async def on_member_join(member):
    guild = member.guild
    unverified_role = discord.utils.get(guild.roles, name="Unverified")
    if unverified_role:
        try:
            await member.add_roles(unverified_role)
        except:
            pass

# نظام التفعيل التلقائي عند الكتابة في الروم المخصص فقط
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # التحقق من أن الرسالة أُرسلت في الروم المحدد للأيدي
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

# نافذة تسجيل الشخصية وتوليد رتبة GD | الزرقاء
class RegistrationModal(discord.ui.Modal, title='إنشاء شخصية جديدة'):
    first_name = discord.ui.TextInput(label='الاسم الأول (بالإنجليزي)', placeholder='First Name...', min_length=2)
    last_name = discord.ui.TextInput(label='الاسم الثاني (بالإنجليزي)', placeholder='Last Name...', min_length=2)
    birthdate = discord.ui.TextInput(label='مواليد الشخصية', placeholder='مثال: 1998/05/12')
    birthplace = discord.ui.TextInput(label='مكان الولادة', placeholder='أدخل مكان الولادة...')
    bio = discord.ui.TextInput(label='فكرة الشخصية', style=discord.TextStyle.paragraph, placeholder='اكتب قصة شخصيتك هنا...')

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        guild = interaction.guild
        
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

        full_name_eng = f"GD | {self.first_name.value} {self.last_name.value}"

        c.execute("INSERT INTO players (discord_id, identity_id, first_name, last_name, birthdate, birthplace, bio, balance, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                  (user_id, new_identity, self.first_name.value, self.last_name.value, self.birthdate.value, self.birthplace.value, self.bio.value, 1000, 'active'))
        conn.commit()
        
        try:
            blue_role = await guild.create_role(name=full_name_eng, color=discord.Color.blue(), reason="رتبة هوية اللاعب")
            member = interaction.user
            await member.add_roles(blue_role)
            
            verified_role = discord.utils.get(guild.roles, name="Verified")
            unverified_role = discord.utils.get(guild.roles, name="Unverified")
            if verified_role:
                await member.add_roles(verified_role)
            if unverified_role and unverified_role in member.roles:
                await member.remove_roles(unverified_role)

            game_categories_names = ["gt | phone", "gt | command", "gt | on display", "gt | theft", "collection", "gt | justice team"]
            for cat in guild.categories:
                if any(name in cat.name.lower() for name in game_categories_names):
                    await cat.set_permissions(blue_role, read_messages=True)

        except Exception as e:
            print(f"خطأ في إنشاء رتبة الهوية والصلاحيات: {e}")

        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(
                f"📇 **تم إنشاء هوية وتفعيل العضو وتحديث صلاحياته:** {interaction.user.mention}\n"
                f"🆔 **رقم الهوية:** `{new_identity}`\n"
                f"👤 **الاسم:** {full_name_eng}\n"
                f"📅 **المواليد:** {self.birthdate.value}"
            )
            
        await interaction.response.send_message(f"✅ تم إنشاء شخصيتك بنجاح! رقم هويتك: **{new_identity}** وتم منحك رتبة الهوية الزرقاء وتفعيلك بنجاح.", ephemeral=True)

class CharacterSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Create Character", description="لإنشاء شخصية جديدة (بحد أقصى 3)"),
            discord.SelectOption(label="Show identity", description="لعرض الهويات المسجلة")
        ]
        super().__init__(placeholder="Choose an action you want to make", options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        if self.values[0] == "Create Character":
            await interaction.response.send_modal(RegistrationModal())
        elif self.values[0] == "Show identity":
            c.execute("SELECT identity_id, first_name, last_name, birthdate, birthplace, balance FROM players WHERE discord_id = ?", (user_id,))
            players = c.fetchall()
            if players:
                text = "هوياتك المسجلة:\n"
                for idx, p in enumerate(players, 1):
                    text += f"\n**الشخصية {idx}:**\n- 🆔 الهوية: `{p[0]}`\n- 👤 الاسم: GD | {p[1]} {p[2]}\n- 📅 المواليد: {p[3]}\n- 💰 الرصيد: {p[5]}\n"
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
 
