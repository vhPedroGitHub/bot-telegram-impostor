#!/usr/bin/env python3
"""
Bot de Telegram para jugar al Impostor
Administra grupos de Telegram para el juego de roles donde hay impostores y ciudadanos.
"""

import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Poll
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    PollAnswerHandler,
    ContextTypes,
    filters
)
from telegram.constants import ChatType
from game import ImpostorGame
from config import BOT_TOKEN, MSG_IMPOSTOR, MSG_CITIZEN
import traceback

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Diccionario para almacenar juegos activos por chat_id
active_games = {}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start - Inicia un nuevo juego"""
    chat = update.effective_chat
    user = update.effective_user
    
    # Solo funciona en grupos
    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update.message.reply_text("❌ Este bot solo funciona en grupos de Telegram.")
        return
    
    # Solo administradores pueden iniciar el juego
    if not await is_admin(context.bot, chat.id, user.id):
        await update.message.reply_text("❌ Solo los administradores pueden iniciar el juego.")
        return
    
    # Verificar si ya hay un juego activo
    if chat.id in active_games:
        await update.message.reply_text("⚠️ Ya hay un juego activo en este grupo. Usa /cancel para cancelarlo.")
        return
    
    # Crear nuevo juego
    game = ImpostorGame(chat.id)
    active_games[chat.id] = game
    
    # Crear encuesta para unirse al juego
    poll_message = await context.bot.send_poll(
        chat_id=chat.id,
        question="🎭 ¿Quieres jugar al Impostor?",
        options=["✅ Sí, quiero jugar", "❌ No"],
        is_anonymous=False,
        allows_multiple_answers=False,
        type=Poll.REGULAR
    )
    
    game.poll_message_id = poll_message.message_id
    
    # Crear botón para que el admin pueda continuar
    keyboard = [[InlineKeyboardButton("▶️ Continuar al siguiente paso", callback_data="continue_game")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🎮 **¡NUEVO JUEGO DE IMPOSTOR!**\n\n"
        f"📊 Los jugadores tienen 3 minutos para unirse o hasta que el admin presione 'Continuar'.\n"
        f"👥 Mínimo 3 jugadores para empezar.\n\n"
        f"🔸 **¿Cómo jugar?**\n"
        f"• Algunos serán impostores (no conocen la palabra)\n"
        f"• Otros serán ciudadanos (conocen la palabra secreta)\n"
        f"• Los impostores deben actuar como si supieran la palabra\n"
        f"• Al final de cada ronda, votan para eliminar al impostor\n\n"
        f"**Vota en la encuesta de arriba para participar** ⬆️",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    # Programar auto-continuación después de 3 minutos
    context.job_queue.run_once(auto_continue_game, 180, data=chat.id)

async def poll_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja las respuestas a las encuestas"""
    poll_answer = update.poll_answer
    user = update.poll_answer.user
    
    # Buscar el juego correspondiente a esta encuesta
    game = None
    chat_id = None
    
    for cid, g in active_games.items():
        if hasattr(g, 'poll_message_id') and g.poll_message_id == poll_answer.poll_id:
            game = g
            chat_id = cid
            break
        elif hasattr(g, 'voting_poll_id') and g.voting_poll_id == poll_answer.poll_id:
            game = g
            chat_id = cid
            break
    
    if not game:
        return
    
    # Si es la encuesta de unirse al juego
    if hasattr(game, 'poll_message_id') and game.poll_message_id == poll_answer.poll_id:
        if poll_answer.option_ids and poll_answer.option_ids[0] == 0:  # "Sí, quiero jugar"
            if user.id not in game.players:
                game.add_player(user.id, user.first_name or user.username or "Jugador")
                logger.info(f"Jugador {user.first_name} se unió al juego en chat {chat_id}")
    
    # Si es una encuesta de votación durante el juego
    elif hasattr(game, 'voting_poll_id') and game.voting_poll_id == poll_answer.poll_id:
        if poll_answer.option_ids and game.state == "voting":
            voted_player_index = poll_answer.option_ids[0]
            game.add_vote(user.id, voted_player_index)

async def continue_game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback para continuar el juego después de la encuesta"""
    query = update.callback_query
    user = query.from_user
    chat_id = query.message.chat_id
    
    await query.answer()
    
    # Verificar permisos de administrador
    if not await is_admin(context.bot, chat_id, user.id):
        await query.edit_message_text("❌ Solo los administradores pueden continuar el juego.")
        return
    
    if chat_id not in active_games:
        await query.edit_message_text("❌ No hay juego activo en este chat.")
        return
    
    game = active_games[chat_id]
    
    if len(game.players) < 3:
        await query.edit_message_text(
            f"❌ Se necesitan al menos 3 jugadores para comenzar.\n"
            f"Jugadores actuales: {len(game.players)}"
        )
        return
    
    # Mostrar configuración del juego
    max_impostors = max(1, len(game.players) // 3)  # Máximo 1/3 de impostores
    
    keyboard = []
    for i in range(1, max_impostors + 1):
        keyboard.append([InlineKeyboardButton(f"👹 {i} impostor(es)", callback_data=f"impostors_{i}")])
    
    await query.edit_message_text(
        f"⚙️ **CONFIGURACIÓN DEL JUEGO**\n\n"
        f"👥 Jugadores: {len(game.players)}\n"
        f"📝 Jugadores: {', '.join([p['name'] for p in game.players.values()])}\n\n"
        f"🎯 Selecciona el número de impostores:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def set_impostors_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback para establecer número de impostores"""
    query = update.callback_query
    chat_id = query.message.chat_id
    
    await query.answer()
    
    if chat_id not in active_games:
        return
    
    game = active_games[chat_id]
    num_impostors = int(query.data.split('_')[1])
    game.num_impostors = num_impostors
    
    # Ahora seleccionar número de rondas
    keyboard = []
    for rounds in range(2, 6):  # 2 a 5 rondas
        keyboard.append([InlineKeyboardButton(f"🔄 {rounds} rondas", callback_data=f"rounds_{rounds}")])
    
    await query.edit_message_text(
        f"⚙️ **CONFIGURACIÓN DEL JUEGO**\n\n"
        f"👥 Jugadores: {len(game.players)}\n"
        f"👹 Impostores: {num_impostors}\n"
        f"👤 Ciudadanos: {len(game.players) - num_impostors}\n\n"
        f"🔄 Selecciona el número de rondas:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def set_rounds_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback para establecer número de rondas y empezar el juego"""
    query = update.callback_query
    chat_id = query.message.chat_id
    
    await query.answer()
    
    if chat_id not in active_games:
        return
    
    game = active_games[chat_id]
    num_rounds = int(query.data.split('_')[1])
    game.max_rounds = num_rounds
    
    # Empezar el juego
    await start_game_rounds(context.bot, chat_id, game, query)

async def start_game_rounds(bot, chat_id, game, query=None):
    """Inicia las rondas del juego"""
    try:
        # Asignar roles y palabra
        game.assign_roles()
        
        if query:
            await query.edit_message_text(
                f"🎮 **INICIANDO JUEGO**\n\n"
                f"👥 Jugadores: {len(game.players)}\n"
                f"👹 Impostores: {game.num_impostors}\n"
                f"🔄 Rondas: {game.max_rounds}\n"
                f"📝 Palabra secreta: ||{game.current_word}||\n\n"
                f"📨 Enviando roles por privado...",
                parse_mode='Markdown'
            )
        
        # Enviar roles a cada jugador por privado
        for player_id, player_data in game.players.items():
            try:
                if player_data['role'] == 'impostor':
                    await bot.send_message(player_id, MSG_IMPOSTOR)
                else:
                    await bot.send_message(player_id, MSG_CITIZEN.format(word=game.current_word))
            except Exception as e:
                logger.warning(f"No se pudo enviar mensaje privado a {player_id}: {e}")
                # Informar en el grupo que el jugador debe iniciar chat con el bot
                await bot.send_message(
                    chat_id, 
                    f"⚠️ @{player_data['name']}: Debes enviar /start al bot en privado para recibir tu rol."
                )
        
        # Esperar 10 segundos
        await asyncio.sleep(10)
        
        # Empezar primera ronda
        await start_round(bot, chat_id, game)
        
    except Exception as e:
        logger.error(f"Error iniciando juego: {e}\n{traceback.format_exc()}")
        await bot.send_message(chat_id, f"❌ Error al iniciar el juego: {str(e)}")

async def start_round(bot, chat_id, game):
    """Inicia una nueva ronda"""
    game.start_new_round()
    
    await bot.send_message(
        chat_id,
        f"🎯 **RONDA {game.current_round}/{game.max_rounds}**\n\n"
        f"📝 Palabra secreta: ||{game.current_word}||\n\n"
        f"🗣️ Es el turno de **{game.get_current_player_name()}**\n"
        f"💬 Solo esta persona puede escribir ahora.\n"
        f"⏰ Escribe una palabra relacionada con la palabra secreta (sin revelarla).",
        parse_mode='Markdown'
    )

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja todos los mensajes durante el juego"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    message_text = update.message.text
    
    if chat_id not in active_games:
        return
    
    game = active_games[chat_id]
    
    # Solo durante las rondas de juego
    if game.state == "playing_round":
        # Solo puede escribir el jugador actual
        if user_id != game.current_player:
            await update.message.delete()
            return
        
        # Verificar si dijo la palabra secreta
        if game.current_word.lower() in message_text.lower():
            await update.message.reply_text(
                f"🎯 **¡{game.get_current_player_name()} dijo la palabra secreta!**\n\n"
                f"🏆 **¡Los IMPOSTORES han ganado!**\n"
                f"📝 La palabra era: **{game.current_word}**\n\n"
                f"👹 Impostores: {', '.join([game.players[p]['name'] for p in game.impostors])}\n"
                f"👤 Ciudadanos: {', '.join([game.players[p]['name'] for p in game.citizens])}",
                parse_mode='Markdown'
            )
            await end_game(chat_id)
            return
        
        # Pasar al siguiente jugador
        game.next_player()
        
        if game.all_players_played():
            # Todos jugaron, iniciar discusión
            await start_discussion(context.bot, chat_id, game)
        else:
            # Siguiente turno
            await update.message.reply_text(
                f"✅ Turno de **{game.get_current_player_name()}**\n"
                f"💬 Solo esta persona puede escribir ahora.",
                parse_mode='Markdown'
            )

async def start_discussion(bot, chat_id, game):
    """Inicia la fase de discusión"""
    game.state = "discussing"
    
    keyboard = [[InlineKeyboardButton("🗳️ Votar ahora", callback_data="start_voting")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await bot.send_message(
        chat_id,
        f"💭 **TIEMPO DE DISCUSIÓN**\n\n"
        f"🗣️ Todos pueden hablar ahora para decidir quién es el impostor.\n"
        f"⏰ Tienen 2 minutos o hasta que el admin presione 'Votar ahora'.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    # Auto-votar después de 2 minutos
    context = bot._app_context if hasattr(bot, '_app_context') else None
    if context and hasattr(context, 'job_queue'):
        context.job_queue.run_once(auto_start_voting, 120, data=chat_id)

async def start_voting_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback para iniciar votación"""
    query = update.callback_query
    chat_id = query.message.chat_id
    user = query.from_user
    
    await query.answer()
    
    if not await is_admin(context.bot, chat_id, user.id):
        return
    
    if chat_id not in active_games:
        return
    
    await start_voting(context.bot, chat_id, active_games[chat_id], query)

async def start_voting(bot, chat_id, game, query=None):
    """Inicia la votación"""
    game.state = "voting"
    game.votes.clear()
    
    # Crear opciones de votación
    options = [f"{player['name']}" for player in game.players.values()]
    
    poll = await bot.send_poll(
        chat_id=chat_id,
        question="🗳️ ¿Quién crees que es el impostor?",
        options=options,
        is_anonymous=False,
        allows_multiple_answers=False,
        type=Poll.REGULAR
    )
    
    game.voting_poll_id = poll.poll.id
    
    if query:
        await query.edit_message_text("🗳️ **VOTACIÓN INICIADA**\n\nVoten en la encuesta de arriba.")
    
    # Auto-terminar votación después de 1 minuto
    await asyncio.sleep(60)
    await end_voting(bot, chat_id, game)

async def end_voting(bot, chat_id, game):
    """Termina la votación y procesa resultados"""
    if chat_id not in active_games or game.state != "voting":
        return
    
    # Parar la encuesta
    try:
        await bot.stop_poll(chat_id, game.voting_poll_id)
    except:
        pass
    
    # Procesar votos y encontrar al más votado
    most_voted_player = game.get_most_voted_player()
    
    if most_voted_player and most_voted_player in game.impostors:
        # ¡Atraparon a un impostor!
        await bot.send_message(
            chat_id,
            f"🎯 **¡IMPOSTOR ELIMINADO!**\n\n"
            f"👹 **{game.players[most_voted_player]['name']}** era impostor.\n\n"
            f"🏆 **¡Los CIUDADANOS han ganado esta ronda!**",
            parse_mode='Markdown'
        )
        
        if game.current_round >= game.max_rounds:
            await bot.send_message(
                chat_id,
                f"🎮 **¡JUEGO TERMINADO!**\n\n"
                f"🏆 **¡VICTORIA DE LOS CIUDADANOS!**\n\n"
                f"👹 Impostores: {', '.join([game.players[p]['name'] for p in game.impostors])}\n"
                f"👤 Ciudadanos: {', '.join([game.players[p]['name'] for p in game.citizens])}",
                parse_mode='Markdown'
            )
            await end_game(chat_id)
        else:
            # Siguiente ronda
            await asyncio.sleep(3)
            await start_round(bot, chat_id, game)
    else:
        # No atraparon al impostor
        elimiando_msg = ""
        if most_voted_player:
            elimiando_msg = f"👤 **{game.players[most_voted_player]['name']}** era ciudadano."
        
        if game.current_round >= game.max_rounds:
            # Juego terminado, ganan los impostores
            await bot.send_message(
                chat_id,
                f"❌ **IMPOSTOR NO DESCUBIERTO**\n\n"
                f"{elimiando_msg}\n\n"
                f"🎮 **¡JUEGO TERMINADO!**\n"
                f"🏆 **¡VICTORIA DE LOS IMPOSTORES!**\n\n"
                f"👹 Impostores: {', '.join([game.players[p]['name'] for p in game.impostors])}\n"
                f"👤 Ciudadanos: {', '.join([game.players[p]['name'] for p in game.citizens])}",
                parse_mode='Markdown'
            )
            await end_game(chat_id)
        else:
            # Siguiente ronda
            await bot.send_message(
                chat_id,
                f"❌ **IMPOSTOR NO DESCUBIERTO**\n\n"
                f"{elimiando_msg}\n"
                f"🔄 Continuamos a la siguiente ronda...",
                parse_mode='Markdown'
            )
            await asyncio.sleep(3)
            await start_round(bot, chat_id, game)

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /cancel - Cancela el juego actual"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    if not await is_admin(context.bot, chat_id, user.id):
        await update.message.reply_text("❌ Solo los administradores pueden cancelar el juego.")
        return
    
    if chat_id in active_games:
        del active_games[chat_id]
        await update.message.reply_text("🚫 **Juego cancelado**")
    else:
        await update.message.reply_text("❌ No hay juego activo para cancelar.")

async def end_meet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /end-meet - Termina la discusión y va a votar"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    if not await is_admin(context.bot, chat_id, user.id):
        await update.message.reply_text("❌ Solo los administradores pueden usar este comando.")
        return
    
    if chat_id not in active_games:
        await update.message.reply_text("❌ No hay juego activo.")
        return
    
    game = active_games[chat_id]
    if game.state == "discussing":
        await start_voting(context.bot, chat_id, game)
    else:
        await update.message.reply_text("❌ No estamos en fase de discusión.")

async def is_admin(bot, chat_id, user_id):
    """Verifica si el usuario es administrador del grupo"""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except:
        return False

async def auto_continue_game(context):
    """Auto-continúa el juego después de 3 minutos"""
    chat_id = context.job.data
    if chat_id in active_games:
        game = active_games[chat_id]
        if len(game.players) >= 3:
            # Simular click en continuar
            # Esta funcionalidad requeriría más implementación
            pass

async def auto_start_voting(context):
    """Auto-inicia votación después de 2 minutos"""
    chat_id = context.job.data
    if chat_id in active_games:
        game = active_games[chat_id]
        if game.state == "discussing":
            await start_voting(context.bot, chat_id, game)

async def end_game(chat_id):
    """Termina y limpia el juego"""
    if chat_id in active_games:
        del active_games[chat_id]

def main():
    """Función principal del bot"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN no encontrado. Verifica tu archivo .env")
        return
    
    # Crear aplicación
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Agregar handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CommandHandler("end_meet", end_meet_command))
    
    # Callbacks
    application.add_handler(CallbackQueryHandler(continue_game_callback, pattern="^continue_game$"))
    application.add_handler(CallbackQueryHandler(set_impostors_callback, pattern="^impostors_"))
    application.add_handler(CallbackQueryHandler(set_rounds_callback, pattern="^rounds_"))
    application.add_handler(CallbackQueryHandler(start_voting_callback, pattern="^start_voting$"))
    
    # Handlers de encuestas y mensajes
    application.add_handler(PollAnswerHandler(poll_answer_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
    
    # Iniciar bot
    logger.info("Bot iniciado")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()