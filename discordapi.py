import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

# Import AudioRecorder
from discord.ext.audiorec import NariveVoiceClient
from discord.ext.audiorec import AudioRecorder

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)
discordToken = os.getenv("DISCORD_TOKEN")
if discordToken is None:
    raise ValueError("DISCORD_TOKEN environment variable not set.")

# Register the AudioRecorder cog
@bot.event
async def on_ready():
    await bot.add_cog(audiorec.AudioRecorder(bot))
    print(f"Logged in as {bot.user}")

@bot.command()
async def join(ctx):
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send("Joined the voice channel!")
    else:
        await ctx.send("You are not in a voice channel.")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Left the voice channel.")
    else:
        await ctx.send("I'm not in a voice channel.")

@commands.command()
async def rec(self, ctx: commands.Context):
    """Start recording"""
    ctx.voice_client.record(lambda e: print(f"Exception: {e}"))
        
    await ctx.send(f'Start Recording')

    await asyncio.sleep(30)

    await ctx.invoke(self.bot.get_command('stop'))

@commands.command()
async def stop(self, ctx: commands.Context):
    """Stops and disconnects the bot from voice"""
    if not ctx.voice_client.is_recording():
        return
    await ctx.send(f'Stop Recording')

    wav_bytes = await ctx.voice_client.stop_record()

    wav_file = discord.File(io.BytesIO(wav_bytes), filename="Recorded.wav")

    await ctx.send(file=wav_file)


@rec.before_invoke
async def ensure_voice(self, ctx: commands.Context):
    if ctx.voice_client is None:
        if ctx.author.voice: # type: ignore
            await ctx.author.voice.channel.connect(cls=NativeVoiceClient) # type: ignore
        else:
            await ctx.send("You are not connected to a voice channel.")
            raise commands.CommandError("Author not connected to a voice channel.")
    elif ctx.voice_client.is_playing():
         ctx.voice_client.stop()

bot.run(discordToken)