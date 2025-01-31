import discord
from discord.ext import commands
from discord.utils import get
from dotenv import load_dotenv
import os
import json

# Cargar variables de entorno desde .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Configuración del bot
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.guild_messages = True
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Configuración de archivos
CHANNELS_FILE = "channels.json"
TICKET_CATEGORY_NAME = "Tickets"
LOG_CHANNEL_NAME = "ticket-logs"
SUGGESTION_CHANNEL_ID = 1334340031879446540

# Funciones para manejar los canales

def load_channels():
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, "r") as file:
            return json.load(file)
    return {}

def save_channels(channels):
    with open(CHANNELS_FILE, "w") as file:
        json.dump(channels, file, indent=4)

registered_channels = load_channels()

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

# Comando para registrar un canal
@bot.command()
@commands.has_permissions(administrator=True)
async def registrar_canal(ctx, canal_id: int, *, nombre: str):
    canal = bot.get_channel(canal_id)
    if canal:
        registered_channels[nombre] = canal_id
        save_channels(registered_channels)
        await ctx.send(f"Canal registrado: **{nombre}** con ID `{canal_id}`.")
    else:
        await ctx.send("El canal no existe o el ID no es válido.")

# Comando para enviar mensajes embebidos
@bot.command()
async def enviar(ctx, nombre: str, *, mensaje: str):
    canal_id = registered_channels.get(nombre)
    if canal_id:
        canal = bot.get_channel(canal_id)
        if canal:
            embed = discord.Embed(
                title="[LATAMRUST] VANILLA #1",
                description=mensaje,
                color=discord.Color.blurple()
            )
            embed.set_footer(text="👉 Recuerda siempre respetar las reglas para disfrutar del servidor.")
            icon_url = "https://cdn.discordapp.com/attachments/1328162644267499561/1333520754267918459/image.png"
            embed.set_thumbnail(url=icon_url)
            await canal.send(embed=embed)
            await ctx.send(f"Mensaje enviado al canal **{nombre}**.", ephemeral=True)
        else:
            await ctx.send("No se pudo encontrar el canal.")
    else:
        await ctx.send(f"No hay ningún canal registrado con el nombre **{nombre}**.")

# Comando para crear encuestas
@bot.command()
async def encuesta(ctx, pregunta: str, *opciones):
    if len(opciones) < 2:
        await ctx.send("¡Debes proporcionar al menos dos opciones!")
        return
    elif len(opciones) > 10:
        await ctx.send("¡No puedes proporcionar más de 10 opciones!")
        return
    
    embed = discord.Embed(title="📊 Encuesta", description=pregunta, color=discord.Color.green())
    reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for i, opcion in enumerate(opciones):
        embed.add_field(name=f"{reactions[i]} {opcion}", value="​", inline=False)
    encuesta_msg = await ctx.send(embed=embed)
    for i in range(len(opciones)):
        await encuesta_msg.add_reaction(reactions[i])
    await ctx.send("Encuesta creada exitosamente.")

# Sistema de tickets
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.primary, custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
        ticket_category = get(guild.categories, name=TICKET_CATEGORY_NAME)

        # ID del rol que debe tener acceso al ticket
        role_id = 1325439150668906549
        role = guild.get_role(role_id)
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
            role: discord.PermissionOverwrite(view_channel=True, send_messages=True)  # El rol tiene acceso
        }

        ticket_channel = await guild.create_text_channel(f"ticket-{user.name}", category=ticket_category, overwrites=overwrites)
        await ticket_channel.send(f"¡Hola {user.mention}, gracias por abrir un ticket!", view=CloseTicketView())
        await interaction.response.send_message(f"Tu ticket ha sido creado: {ticket_channel.mention}", ephemeral=True)

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Cerrar Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        if not channel.name.startswith("ticket-"):
            await interaction.response.send_message("Este no es un canal de ticket.", ephemeral=True)
            return
        
        # Canal de logs donde se guardarán los eventos de cierre de tickets
        log_channel = discord.utils.get(interaction.guild.text_channels, name=LOG_CHANNEL_NAME)
        if log_channel:
            # Crear embed para el log
            embed = discord.Embed(
                title="Ticket Cerrado",
                description=f"**Ticket:** {channel.mention}\n**Cerrado por:** {interaction.user.mention}\n**Fecha:** {interaction.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
                color=discord.Color.red()
            )
            embed.set_footer(text="Sistema de tickets LATAM RUST")
            await log_channel.send(embed=embed)
        
        # Eliminar el canal de ticket
        await channel.delete()
        await interaction.response.send_message("El ticket ha sido cerrado y eliminado.", ephemeral=True)

# Comando para mostrar el panel de tickets
@bot.command()
@commands.has_permissions(administrator=True)
async def panel(ctx):
    embed = discord.Embed(title="Sistema de Tickets", description="Presione aquí para abrir soporte.", color=0x4d4dff)
    icon_url = "https://cdn.discordapp.com/attachments/1328162644267499561/1333520754267918459/image.png"
    embed.set_thumbnail(url=icon_url)
    view = TicketView()
    await ctx.send(embed=embed, view=view)

# Comando para sugerencias
class SuggestionModal(discord.ui.Modal, title="Enviar una sugerencia"):
    suggestion = discord.ui.TextInput(label="Tu sugerencia", style=discord.TextStyle.paragraph, required=True)
    
    async def on_submit(self, interaction: discord.Interaction):
        suggestion_channel = bot.get_channel(SUGGESTION_CHANNEL_ID)
        if suggestion_channel:
            embed = discord.Embed(
                title="📌 Nueva Sugerencia",
                description=self.suggestion.value,
                color=discord.Color.blurple()
            )
            embed.set_footer(text=f"📝 Enviado por {interaction.user}")
            icon_url = "https://cdn.discordapp.com/attachments/1328162644267499561/1333520754267918459/image.png"
            embed.set_thumbnail(url=icon_url)
            await suggestion_channel.send(embed=embed)
            await interaction.response.send_message("✅ Sugerencia enviada con éxito!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No se encontró el canal de sugerencias.", ephemeral=True)

@bot.command()
async def sugerencia(ctx):
    await ctx.send(
        "📝 Para enviar una sugerencia, presiona el botón a continuación.",
        view=discord.ui.View().add_item(
            discord.ui.Button(label="Enviar Sugerencia", style=discord.ButtonStyle.primary, custom_id="send_suggestion")
        )
    )

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.data and interaction.data.get("custom_id") == "send_suggestion":
        await interaction.response.send_modal(SuggestionModal())

# Iniciar el bot
bot.run(TOKEN)
