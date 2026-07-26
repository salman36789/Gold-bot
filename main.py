import discord
from discord.ext import commands
import sqlite3
import os
import random
import asyncio
import time

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

is_building = False
last_build_time = 0

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    print("البوت جاهز مع الرتب الإدارية المنظمة والصلاحيات الكاملة!")

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

@bot.command(name="build")
async def build_server(ctx):
    # حماية أمر البناء لمالك السيرفر فقط
    if ctx.author != ctx.guild.owner:
        await ctx.send("❌ عذراً، هذا الأمر مخصص لمالك السيرفر (Owner) فقط!", delete_after=5)
        return

    global is_building, last_build_time
    current_time = time.time()
    
    if is_building or (current_time - last_build_time < 15):
        return

    is_building = True
    last_build_time = current_time
    
    await ctx.send("🔄 جاري فرمتة السيرفر، ضبط الرتب الإدارية (أصفر/أحمر/أخضر)، وبناء الأقسام...")
    
    try:
        guild = ctx.guild
        
        # 1. الرتب الأساسية للأعضاء
        verified_role = discord.utils.get(guild.roles, name="Verified")
        if not verified_role:
            verified_role = await guild.create_role(name="Verified", color=discord.Color.green(), reason="Verified members role")
        else:
            await verified_role.edit(color=discord.Color.green())
            
        unverified_role = discord.utils.get(guild.roles, name="Unverified")
        if not unverified_role:
            unverified_role = await guild.create_role(name="Unverified", color=discord.Color.red(), reason="Unverified members role")
        else:
            await unverified_role.edit(color=discord.Color.red())

        # 2. الرتب الإدارية المرتبة بألوان ذهبية وصفراء مميزة
        admin_roles_data = [
            ("👑 ┃ Owner", discord.Color.gold(), discord.Permissions(administrator=True)),
            ("🛡️ ┃ High Admin", discord.Color.orange(), discord.Permissions(manage_guild=True, manage_roles=True, ban_members=True, kick_members=True)),
            ("⚡ ┃ Admin", discord.Color.yellow(), discord.Permissions(manage_messages=True, kick_members=True)),
            ("🔨 ┃ Moderator", discord.Color.light_embed(), discord.Permissions(manage_messages=True))
        ]
        
        for r_name, r_color, r_perms in admin_roles_data:
            r = discord.utils.get(guild.roles, name=r_name)
            if not r:
                await guild.create_role(name=r_name, color=r_color, permissions=r_perms, reason="Administrative role")
            else:
                await r.edit(color=r_color, permissions=r_perms)

        # 3. حذف كافة الرومات والأقسام القديمة لإعادة البناء النظيف
        for channel in list(guild.channels):
            try:
                await channel.delete()
                await asyncio.sleep(0.4)
            except:
                pass
                
        for category in list(guild.categories):
            try:
                await category.delete()
                await asyncio.sleep(0.4)
            except:
                pass

        await asyncio.sleep(1)

        structure = {
            "Gold Town | Rules": [
                ("🟥 ┃ rules", "text"),
                ("📜 ┃ new-rules", "text"),
                ("🔗 ┃ pinned", "text"),
                ("🆔 ┃ enter-id", "text")
            ],
            "Gold Town | Ads": [
                ("📢 ┃ announcement", "text"),
                ("👷 ┃ updates", "text"),
                ("📄 ┃ merges", "text"),
                ("🔍 ┃ hints", "text"),
                ("🔮 ┃ boosters", "text"),
                ("🔗 ┃ partners", "text")
            ],
            "Gold Town Identity": [
                ("📇 ┃ character-rules", "text"),
                ("📇 ┃ create-character", "text"),
                ("📇 ┃ تزوير-الهوية", "text")
            ],
            "Gold Town | General": [
                ("🔔 ┃ Notices", "text"),
                ("✈️ ┃ Trips", "text")
            ],
            "GT | Support": [
                ("📧 ┃ tickets", "text"),
                ("❗ ┃ support-chat", "text")
            ],
            "GT | Submit Staff": [
                ("📢 ┃ staff-ads", "text"),
                ("🖥️ ┃ submit-management", "text")
            ],
            "Gold Town Public": [
                ("💬 ┃ general-chat", "text"),
                ("💸 ┃ credits", "text"),
                ("📿 ┃ athkar", "text"),
                ("💭 ┃ suggestions", "text"),
                ("🎡 ┃ events", "text")
            ],
            "Social": [
                ("🎥 ┃ tiktok", "text"),
                ("📺 ┃ live-now", "text")
            ],
            "GT | Phone": [
                ("📄 ┃ News", "text"),
                ("📱 ┃ Phone", "text"),
                ("📱 ┃ X", "text"),
                ("📱 ┃ X-Video", "text")
            ],
            "GT | Command": [
                ("⚙️ ┃ Command", "text"),
                ("🎒 ┃ Inventory", "text"),
                ("🏪 ┃ Shops", "text"),
                ("🏦 ┃ Bank", "text"),
                ("🏥 ┃ Hospital", "text")
            ],
            "GT | On display": [
                ("🏠 ┃ Real-Estate", "text"),
                ("🚗 ┃ Car-Showroom", "text")
            ],
            "GT | Theft": [
                ("📜 ┃ Robbery-Rules", "text"),
                ("🚨 ┃ Reports", "text")
            ],
            "Collection": [
                ("🟧 ┃ Factory-Rules", "text"),
                ("🟧 ┃ Factory-Location", "text"),
                ("🟧 ┃ Factory", "text")
            ],
            "GT | Justice Team": [
                ("📄 ┃ Justice-Cases", "text"),
                ("🏛️ ┃ Presenting-Justice", "text"),
                ("📄 ┃ court-orders", "text"),
                ("🧑‍⚖️ ┃ Radio-Court", "voice"),
                ("🧑‍⚖️ ┃ Radio-Judges", "voice")
            ]
        }

        identity_roles = [role for role in guild.roles if role.name.startswith("GD |")]

        for category_name, channels in structure.items():
            try:
                if category_name in ["Gold Town | Rules", "Gold Town | Ads", "Gold Town Identity", "Gold Town | General"]:
                    overwrites = {
                        guild.default_role: discord.PermissionOverwrite(read_messages=False),
                        unverified_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                        verified_role: discord.PermissionOverwrite(read_messages=True)
                    }
                    category = await guild.create_category(category_name, overwrites=overwrites)
                else:
                    overwrites = {
                        guild.default_role: discord.PermissionOverwrite(read_messages=False),
                        verified_role: discord.PermissionOverwrite(read_messages=False)
                    }
                    for i_role in identity_roles:
                        overwrites[i_role] = discord.PermissionOverwrite(read_messages=True)

                    category = await guild.create_category(category_name, overwrites=overwrites)
                
                await asyncio.sleep(0.8) 
            except:
                continue

            for ch_name, ch_type in channels:
                try:
                    if ch_type == "text":
                        await guild.create_text_channel(ch_name, category=category)
                    elif ch_type == "voice":
                        await guild.create_voice_channel(ch_name, category=category)
                    await asyncio.sleep(0.4)
                except:
                    pass

        print("✅ تم بناء السيرفر والرتب الإدارية بنجاح كامل!")
    
    finally:
        is_building = False

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.name == "enter-id":
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

            game_categories = [
                "GT | Phone", "GT | Command", "GT | On display", 
                "GT | Theft", "Collection", "GT | Justice Team"
            ]
            for cat_name in game_categories:
                cat = discord.utils.get(guild.categories, name=cat_name)
                if cat:
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
 
