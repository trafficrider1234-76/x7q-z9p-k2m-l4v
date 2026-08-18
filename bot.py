import os
import discord

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    if 'seo' in message.content.lower() or 'web dev' in message.content.lower():
        print(f"Potential Client Found: {message.author} said: {message.content}")

# GitHub Secret se token uthayega
token = os.getenv('DISCORD_TOKEN')
client.run(token)
