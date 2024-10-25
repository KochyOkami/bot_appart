from discord import Client, Embed, Intents
from token_bot import CHANNEL_ID, TOKEN
import asyncio
from crawler import check_for_new_ads, create_connection
# Initialiser les intents
intents = Intents.default()
intents.messages = True  # Permet au bot de recevoir des événements de message
print(TOKEN)
# Initialiser le client Discord avec les intents
client = Client(intents=intents)

async def send_notification(message):
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(embeds=[message])

async def check_for_new_announcements():
    while True:
        connection = create_connection()
        new_ads = check_for_new_ads(connection)
        
        for ad in new_ads:
            embed = Embed(title=ad['title'], description=ad['description'])
            embed.set_image(url=ad['thumbnailUrl'])
            embed.add_field(name="ID", value=ad['id'], inline=False)
            embed.add_field(name="Loyer", value=f"{ad['price']}€", inline=True)
            embed.add_field(name="Dépot garantie", value=f"{ad['safetyDeposit']}€" if ad['safetyDeposit'] is not None else "0€", inline=True)
            embed.add_field(name="Frais d'agence", value=f"{ad['agencyRentalFee']}€" if ad['agencyRentalFee'] is not None else "0€", inline=True)
            embed.add_field(name="Surface", value=f"{ad['surfaceArea']}m²", inline=True)
            embed.add_field(name="Chambre", value=ad['roomsQuantity'], inline=True)
            embed.add_field(name="DPE", value=ad['energyClassification'], inline=True)
            embed.add_field(name="URL", value=ad['url'], inline=False)
            await send_notification(embed)
        connection.close()
        await asyncio.sleep(6*60*60)    
@client.event
async def on_ready():
    print(f'Connecté en tant que {client.user}')
    await check_for_new_announcements()
    

client.run(TOKEN)
