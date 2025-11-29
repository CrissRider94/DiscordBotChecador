# =============== BOT CHECADOR VERSIÓN ESTABLE ===============
# Compatible con discord.py 2.3+
# Corrige:
# - Doble botones
# - Doble entrada
# - Salida sin entrada
# - Mensajes duplicados
# - Vistas persistentes
# - JSON corrupto
# =============================================================

import discord
from discord.ext import commands
from discord.ui import Button, View
from discord import app_commands
import json
from datetime import datetime
import pytz

# =========================================
# CONFIGURACIÓN
# =========================================
import os
import pytz
import discord
from discord.ext import commands

# Ahora el bot toma el TOKEN desde variables de entorno (Railway / GitHub)
BOT_TOKEN = os.getenv("TOKEN")   # <--- IMPORTANTE

# Zona horaria
TZ = pytz.timezone("America/Mexico_City")

# IDs de canales (estos NO son secretos, se pueden quedar así)
CHECADOR_CHANNEL_ID = 1444076043995447467
LOGS_CHANNEL_ID = 1444076044268208314

# Intents y bot
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree
# =========================================
# BASE DE DATOS JSON
# =========================================
def cargar():
    try:
        with open("registros.json", "r") as f:
            return json.load(f)
    except:
        return {}

def guardar(db):
    with open("registros.json", "w") as f:
        json.dump(db, f, indent=4)

# =========================================
# BOTÓN DE CIERRE MANUAL
# =========================================
class CerrarSalidaManual(View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = str(user_id)

    @discord.ui.button(label="Cerrar salida manual", style=discord.ButtonStyle.red)
    async def cerrar_manual(self, interaction: discord.Interaction, button):
        user_id = str(interaction.user.id)
        if user_id != self.user_id:
            return await interaction.response.send_message(
                "❌ Solo el dueño puede cerrar su propia salida.",
                ephemeral=True
            )

        db = cargar()

        if "entrada" not in db[user_id]:
            return await interaction.response.send_message(
                "❌ No tienes entrada activa.",
                ephemeral=True
            )

        ahora = datetime.now(TZ)
        entrada_str = db[user_id]["entrada"]
        entrada_dt = datetime.strptime(entrada_str, "%Y-%m-%d %H:%M:%S")
        entrada_dt = TZ.localize(entrada_dt)

        horas_hoy = round((ahora - entrada_dt).total_seconds() / 3600, 2)
        semana = str(ahora.isocalendar().week)

        db[user_id].setdefault("semanas", {}).setdefault(semana, 0)
        db[user_id]["semanas"][semana] += horas_hoy

        del db[user_id]["entrada"]
        guardar(db)

        await interaction.response.send_message(
            f"🟥 Salida cerrada manualmente.\nHoras trabajadas hoy: **{horas_hoy}**",
            ephemeral=True
        )

# =========================================
# BOTONES PRINCIPALES
# =========================================
class ChecadorView(View):
    def __init__(self):
        super().__init__(timeout=None)

    # === BOTÓN ENTRADA ===
    @discord.ui.button(label="Registrar Entrada", style=discord.ButtonStyle.green)
    async def registrar_entrada(self, interaction: discord.Interaction, button):
        user_id = str(interaction.user.id)
        db = cargar()

        # Previene doble entrada
        if user_id in db and "entrada" in db[user_id]:
            return await interaction.response.send_message(
                "❌ Ya tienes una entrada activa.",
                ephemeral=True
            )

        ahora = datetime.now(TZ)
        fecha = ahora.strftime("%Y-%m-%d")
        hora = ahora.strftime("%H:%M:%S")

        db[user_id] = {"entrada": f"{fecha} {hora}"}
        guardar(db)

        await interaction.response.send_message(
            f"🟩 Entrada registrada a las **{hora}**",
            ephemeral=True
        )

        canal_logs = bot.get_channel(LOGS_CHANNEL_ID)
        await canal_logs.send(
            f"🟩 **ENTRADA:** {interaction.user.mention} — {fecha} {hora}"
        )

    # === BOTÓN SALIDA ===
    @discord.ui.button(label="Registrar Salida", style=discord.ButtonStyle.red)
    async def registrar_salida(self, interaction: discord.Interaction, button):
        user_id = str(interaction.user.id)
        db = cargar()

        if user_id not in db or "entrada" not in db[user_id]:
            return await interaction.response.send_message(
                "❌ No tienes entrada activa.",
                ephemeral=True
            )

        ahora = datetime.now(TZ)
        fecha = ahora.strftime("%Y-%m-%d")
        hora = ahora.strftime("%H:%M:%S")

        entrada_str = db[user_id]["entrada"]
        entrada_dt = datetime.strptime(entrada_str, "%Y-%m-%d %H:%M:%S")
        entrada_dt = TZ.localize(entrada_dt)

        horas_hoy = round((ahora - entrada_dt).total_seconds() / 3600, 2)
        semana = str(ahora.isocalendar().week)

        db[user_id].setdefault("semanas", {}).setdefault(semana, 0)
        db[user_id]["semanas"][semana] += horas_hoy

        del db[user_id]["entrada"]
        guardar(db)

        # Enviar reporte por DM
        await interaction.user.send(
            f"📘 **Reporte de hoy**\n"
            f"Entrada: {entrada_str}\n"
            f"Salida: {fecha} {hora}\n"
            f"Horas: {horas_hoy}\n"
            f"Semana {semana}: {db[user_id]['semanas'][semana]}"
        )

        canal_logs = bot.get_channel(LOGS_CHANNEL_ID)
        await canal_logs.send(
            f"🟥 **SALIDA:** {interaction.user.mention} — {fecha} {hora} — {horas_hoy} hrs",
            view=CerrarSalidaManual(user_id)
        )

        await interaction.response.send_message("Salida registrada. Revisa tu DM.", ephemeral=True)

# =========================================
# COMANDO /checador
# =========================================
@tree.command(name="checador", description="Activa el reloj checador.")
async def checador_cmd(interaction: discord.Interaction):
    view = ChecadorView()
    canal = bot.get_channel(CHECADOR_CHANNEL_ID)

    msg = await canal.send("🕒 **Reloj Checador**", view=view)
    await msg.pin()

    await interaction.response.send_message("Checador fijado correctamente.", ephemeral=True)

# =========================================
# READY
# =========================================
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot iniciado como {bot.user}")

# =========================================
# INICIAR BOT
# =========================================
bot.run(BOT_TOKEN)
