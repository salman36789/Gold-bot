import discord
from discord.ext import commands
from discord import ui
import asyncio
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

class PSNModal(ui.Modal, title="PlayStation Verification"):
    psn_id = ui.TextInput(
        label="Enter your PSN ID",
        placeholder="Example: xX_Sultan_Xx",
        required=True,
        max_length=30
    )

    async def on_submit(self, interaction: discord.Interaction):
        ACTIVATED_ROLE_ID = 123456789012345678  
        LOG_CHANNEL_ID = 123456789012345678      

        guild = interaction.guild
        member = interaction.user
        psn_name = self.psn_id.value

        try:
            await member.edit(nick=psn_name)
            role = guild.get_role(ACTIVATED_ROLE_ID)
            if role:
                await member.add_roles(role)

            await interaction.response.send_message(
                f"✅ **Verified Successfully!** Your PSN ID (`{psn_name}`) has been linked.",
                ephemeral=True
            )

            log_channel = guild.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                embed = discord.Embed(
                    title="🎮 New PSN Verification",
                    color=discord.Color.gold(),
                    timestamp=discord.utils.utcnow()
                )
                embed.add_field(name="Discord User:", value=member.mention, inline=False)
                embed.add_field(name="PSN ID:", value=f"`{psn_name}`", inline=False)
                embed.set_thumbnail(url="attachment://logo.png") 
                await log_channel.send(embed=embed)

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to change your nickname or give you roles.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )

class PSNView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Press to activate", 
        style=discord.ButtonStyle.blurple, 
        emoji="🎮", 
        custom_id="psn_press_to_activate"
    )
    async def activate_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(PSNModal())

@bot.tree.command(name="setup-verify", description="إرسال رسالة تفعيل آي دي السوني")
@commands.has_permissions(administrator=True)
async def setup_verify(interaction: discord.Interaction):
    await interaction.response.send_message("🔄 **يرجى الانتظار...** سيقوم البوت بإرسال الرسالة.", ephemeral=True)
    
    upload_prompt = await interaction.channel.send(
        f"**مرحباً {interaction.user.mention}!**\n"
        "يرجى رفع الصورة الذهبية (الشعار) كملف (File Upload) في هذه القناة خلال 60 ثانية لتتم إضافتها."
    )

    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel and m.attachments

    try:
        msg = await bot.wait_for('message', timeout=60.0, check=check)
        attachment = msg.attachments[0]

        if not attachment.content_type.startswith('image/'):
            await interaction.channel.send("❌ هذا ليس ملف صورة، يرجى المحاولة مرة أخرى.")
            return

        embed = discord.Embed(
            color=discord.Color.from_rgb(26, 37, 48) 
        )
        embed.set_image(url="attachment://logo.png")
        
        file = await attachment.to_file(filename="logo.png")
        await interaction.channel.send(embed=embed, view=PSNView(), file=file)
        
        await upload_prompt.delete()
        await msg.delete()

    except asyncio.TimeoutError:
        await upload_prompt.edit(content="❌ انتهى الوقت المحدد ولم يتم رفع الصورة.")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    bot.add_view(PSNView())
    try:
        await bot.tree.sync()
        print("Synced slash commands.")
    except Exception as e:
        print(e)

bot.run(os.getenv("DISCORD_TOKEN"))
