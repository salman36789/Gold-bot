import discord
from discord.ext import commands
import os
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

TRIPS_CHANNEL_ID = 1530770307357343895
NOTIFICATIONS_CHANNEL_ID = 1530770304056557751

IMAGE_URL = "https://cdn.discordapp.com/attachments/1530770297207263305/1531042208252170411/IMG__.jpg?ex=6a67c5ab&is=6a66742b&hm=999c8191853acf2d0d419692f3cbac20a15658b2dad2fe468f5104c4f05ccd13&" 
TRIP_BANNER_URL = "https://cdn.discordapp.com/attachments/1530770297207263305/1531042208252170411/IMG__.jpg?ex=6a67c5ab&is=6a66742b&hm=999c8191853acf2d0d419692f3cbac20a15658b2dad2fe468f5104c4f05ccd13&"

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} - Trip System is Online!')

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
            await interaction.followup.send("❌ لم يتم العثور على روم الرحلات المحدد!", ephemeral=True)
            return

        embed = discord.Embed(title="Games Notifications", color=discord.Color.teal())
        embed.description = (
            "🚀 **- Effect King's Game .**\n\n"
            "بسم الله الرحمن الرحيم ،\n"
            "حياكم الله جميعاً لمن يود الحضور يقوم بتسجيل الدخول بشخصيته.\n\n"
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
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ ليس لديك صلاحية استخدام هذا الزر!", ephemeral=True)
            return
        await interaction.response.send_modal(TripSetupModal())

    @discord.ui.button(label="إعصار", style=discord.ButtonStyle.red, custom_id="btn_hurricane")
    async def hurricane_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ ليس لديك صلاحية استخدام هذا الزر!", ephemeral=True)
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
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ ليس لديك صلاحية استخدام هذا الزر!", ephemeral=True)
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

@bot.command(name="panel")
async def trip_panel(ctx):
    if not ctx.author.guild_permissions.administrator:
        return
    try:
        await ctx.message.delete()
    except:
        pass

    embed = discord.Embed(title="لوحة تحكم إدارة الرحلات", description="استخدم الأزرار أدناه لإدارة الرحلات، الإعصار، والتجديد بكل سهولة:", color=discord.Color.gold())
    await ctx.send(embed=embed, view=AdminTripPanelView())

@bot.command(name="امسح")
async def clear_messages(ctx, amount: int = 10):
    if not ctx.author.guild_permissions.administrator:
        return
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 تم حذف {amount} رسالة بنجاح.")
    await asyncio.sleep(3)
    try:
        await msg.delete()
    except:
        pass

bot.run(os.getenv('TOKEN'))
 
