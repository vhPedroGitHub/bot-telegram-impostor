"""
Configuración del bot de Telegram Impostor
"""
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Token del bot de Telegram
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Configuración del juego
MAX_ROUNDS = 5
MIN_ROUNDS = 2
POLL_DURATION = 180  # 3 minutos en segundos
VOTE_DURATION = 60   # 1 minuto en segundos
DISCUSSION_DURATION = 120  # 2 minutos en segundos
ROLE_REVEAL_DELAY = 10  # 10 segundos para que los jugadores vean su rol

# Mensajes
MSG_IMPOSTOR = "🎭 ¡IMPOSTOR AHORA!!!!\n\nEres un IMPOSTOR. No conoces la palabra secreta. Debes intentar descubrirla sin ser descubierto."
MSG_CITIZEN = "👤 Eres un CIUDADANO\n\nLa palabra secreta es: {word}\n\nDebes dar pistas sin revelar la palabra directamente."
