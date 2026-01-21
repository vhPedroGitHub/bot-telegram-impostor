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
    """Comando /start - Inicia un nuevo juego en grupos o habilita chat privado"""
    chat = update.effective_chat
    user = update.effective_user
    
    # Si es un chat privado, solo confirmar que el bot puede enviar mensajes
    if chat.type == ChatType.PRIVATE:
        await update.message.reply_text(
            f"👋 ¡Hola {user.first_name}!\n\n"
            f"✅ Ahora puedo enviarte mensajes privados.\n"
            f"🎮 Para jugar al Impostor, ve a un grupo y que un admin use /start allí."
        )
        return
    
    # En grupos - iniciar juego
    if chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await update.message.reply_text("❌ Este bot funciona en grupos de Telegram y chats privados.")
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
    
    game.poll_message_id = poll_message.poll.id
    logger.info(f"Created join poll with ID: {poll_message.poll.id} for chat {chat.id}")
    
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
        f"⚠️ **IMPORTANTE:** Todos deben enviar /start al bot en privado para recibir su rol.\n\n"
        f"**Vota en la encuesta de arriba para participar** ⬆️",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    # Programar auto-continuación después de 3 minutos
    if context.job_queue:
        context.job_queue.run_once(auto_continue_game, 180, data=chat.id)

async def poll_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja las respuestas a las encuestas"""
    poll_answer = update.poll_answer
    user = update.poll_answer.user
    
    # Buscar el juego correspondiente a esta encuesta
    game = None
    chat_id = None
    
    logger.info(f"Poll answer recibido: poll_id={poll_answer.poll_id}, user={user.id}, options={poll_answer.option_ids}")
    
    for cid, g in active_games.items():
        logger.info(f"Checking game {cid}: poll_message_id={getattr(g, 'poll_message_id', None)}, voting_poll_id={getattr(g, 'voting_poll_id', None)}")
        if hasattr(g, 'poll_message_id') and g.poll_message_id == poll_answer.poll_id:
            game = g
            chat_id = cid
            logger.info(f"Found matching join game poll for chat {cid}")
            break
        elif hasattr(g, 'voting_poll_id') and g.voting_poll_id == poll_answer.poll_id:
            game = g
            chat_id = cid
            logger.info(f"Found matching voting poll for chat {cid}")
            break
    
    if not game:
        return
    
    # Si es la encuesta de unirse al juego
    if hasattr(game, 'poll_message_id') and game.poll_message_id == poll_answer.poll_id:
        if poll_answer.option_ids and poll_answer.option_ids[0] == 0:  # "Sí, quiero jugar"
            if user.id not in game.players:
                player_name = user.first_name or user.username or f"Jugador{user.id}"
                game.add_player(user.id, player_name)
                logger.info(f"Jugador {player_name} ({user.id}) se unió al juego en chat {chat_id}. Total: {len(game.players)}")
    
    # Si es una encuesta de votación durante el juego
    elif hasattr(game, 'voting_poll_id') and game.voting_poll_id == poll_answer.poll_id:
        if poll_answer.option_ids and game.state == "voting":
            voted_player_index = poll_answer.option_ids[0]
            logger.info(f"Usuario {user.id} votó por índice {voted_player_index}. Orden de jugadores: {game.players_order}")
            game.add_vote(user.id, voted_player_index)
            logger.info(f"Voto registrado. Total votos: {len(game.votes)}")

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
    
    # Verificar que hay suficientes jugadores
    if len(game.players) < 3:
        await query.edit_message_text(
            f"❌ **Jugadores insuficientes**\n\n"
            f"📋 Jugadores actuales: {len(game.players)}\n"
            f"✅ Mínimo requerido: 3\n\n"
            f"📝 Lista actual: {', '.join([p['name'] for p in game.players.values()]) if game.players else 'Ninguno'}"
        )
        return
    
    # Validar configuración del juego
    is_valid, error_msg = game.validate_game_settings()
    if not is_valid:
        await query.edit_message_text(f"❌ Error de configuración: {error_msg}")
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
    user = query.from_user
    
    await query.answer()
    
    # Verificar permisos de administrador
    if not await is_admin(context.bot, chat_id, user.id):
        await query.edit_message_text("❌ Solo los administradores pueden configurar el juego.")
        return
    
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
    user = query.from_user
    
    await query.answer()
    
    # Verificar permisos de administrador
    if not await is_admin(context.bot, chat_id, user.id):
        await query.edit_message_text("❌ Solo los administradores pueden configurar el juego.")
        return
    
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
                f"🔄 Rondas: {game.max_rounds}\n\n"
                f"📨 Enviando roles por privado...",
                parse_mode='Markdown'
            )
        
        # Enviar roles a cada jugador por privado
        failed_private_messages = []
        success_count = 0
        
        for player_id, player_data in game.players.items():
            try:
                if player_data['role'] == 'impostor':
                    await bot.send_message(player_id, MSG_IMPOSTOR)
                else:
                    await bot.send_message(player_id, MSG_CITIZEN.format(word=game.current_word))
                success_count += 1
            except Exception as e:
                logger.warning(f"No se pudo enviar mensaje privado a {player_id}: {e}")
                failed_private_messages.append(player_data['name'])
        
        # Mensaje de estado en el grupo
        status_msg = f"📨 **ROLES ENVIADOS**\n\n✅ {success_count}/{len(game.players)} jugadores recibieron su rol"
        
        if failed_private_messages:
            status_msg += f"\n\n⚠️ Los siguientes jugadores deben enviar /start al bot en privado:\n" + "\n".join([f"• @{name}" for name in failed_private_messages])
        else:
            status_msg += "\n\n🎉 ¡Todos los jugadores recibieron su rol!"
        
        await bot.send_message(chat_id, status_msg)
        
        # Esperar 10 segundos
        await asyncio.sleep(10)
        
        # Empezar primera ronda
        await start_round(bot, chat_id, game)
        
    except Exception as e:
        logger.error(f"Error iniciando juego: {e}\n{traceback.format_exc()}")
        await bot.send_message(chat_id, f"❌ Error al iniciar el juego: {str(e)}")

async def start_round(bot, chat_id, game):
    """Inicia una nueva ronda"""
    # Verificar que el juego esté en estado correcto
    if chat_id not in active_games or game.state not in ["playing_round", "discussing", "voting", "processing_votes"]:
        logger.warning(f"start_round llamado con estado incorrecto: {getattr(game, 'state', 'no_game')}")
        return
    
    game.start_new_round()
    logger.info(f"Iniciando ronda {game.current_round}/{game.max_rounds} para chat {chat_id}")
    
    await bot.send_message(
        chat_id,
        f"🎯 **RONDA {game.current_round}/{game.max_rounds}**\n\n"
        f"️ Es el turno de **{game.get_current_player_name()}**\n"
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
            try:
                await update.message.delete()
                # Enviar mensaje temporal de advertencia
                warning_msg = await context.bot.send_message(
                    chat_id,
                    f"⚠️ Solo {game.get_current_player_name()} puede escribir ahora.\n💡 Usa /next-player para pasar turno."
                )
                # Borrar la advertencia después de 3 segundos
                await asyncio.sleep(3)
                try:
                    await warning_msg.delete()
                except:
                    pass
            except Exception:
                # Ignorar si no se puede borrar el mensaje
                pass
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
        
        # Guardar la palabra dicha
        game.add_word(user_id, message_text)
        
        # Informar que debe usar /next-player
        await update.message.reply_text(
            f"✅ Palabra registrada: **{message_text}**\n👉 Usa /next-player cuando estés listo.",
            parse_mode='Markdown'
        )

async def start_discussion(bot, chat_id, game, context=None):
    """Inicia la fase de discusión"""
    game.state = "discussing"
    
    keyboard = [[InlineKeyboardButton("🗣️ Terminar discusión y votar", callback_data="start_voting")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await bot.send_message(
        chat_id,
        f"💭 **TIEMPO DE DISCUSIÓN**\n\n"
        f"🗣️ Todos pueden hablar ahora para decidir quién es el impostor.\n"
        f"⏰ Tienen 3 minutos o hasta que el admin presione el botón.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    # Programar auto-inicio de votación después de 3 minutos si hay context con job_queue
    if context and context.job_queue:
        context.job_queue.run_once(
            auto_start_voting,
            180,  # 3 minutos
            data=chat_id
        )

async def start_voting_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback para iniciar votación"""
    query = update.callback_query
    chat_id = query.message.chat_id
    user = query.from_user
    
    await query.answer()
    
    if not await is_admin(context.bot, chat_id, user.id):
        await query.edit_message_text("❌ Solo los administradores pueden iniciar la votación.")
        return
    
    if chat_id not in active_games:
        await query.edit_message_text("❌ No hay juego activo.")
        return
    
    game = active_games[chat_id]
    if game.state != "discussing":
        await query.edit_message_text("❌ No estamos en fase de discusión.")
        return
    
    await start_voting(context.bot, chat_id, game, query)
    
    # Programar auto-terminación de votación después de 30 segundos
    if context.job_queue:
        context.job_queue.run_once(
            lambda ctx: end_voting(ctx.bot, chat_id, game), 
            30,  # 30 segundos
            data={'chat_id': chat_id, 'game': game}
        )

async def start_voting(bot, chat_id, game, query=None):
    """Inicia la votación"""
    game.state = "voting"
    game.votes.clear()
    
    # Crear opciones de votación con los nombres en el mismo orden que players_order
    options = [game.players[player_id]['name'] for player_id in game.players_order]
    logger.info(f"Opciones de votación: {options} (orden: {game.players_order})")
    
    poll = await bot.send_poll(
        chat_id=chat_id,
        question="🗳️ ¿Quién crees que es el impostor?",
        options=options,
        is_anonymous=False,
        allows_multiple_answers=False,
        type=Poll.REGULAR
    )
    
    game.voting_poll_id = poll.poll.id
    
    # Crear botón para que admin termine votación
    keyboard = [[InlineKeyboardButton("⏹️ Terminar votación (Admin)", callback_data="end_voting")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.edit_message_text("🗳️ **VOTACIÓN INICIADA**\n\n⏰ Tienen 30 segundos para votar en la encuesta de arriba.")
        await bot.send_message(chat_id, "⚡ Admin puede terminar la votación inmediatamente:", reply_markup=reply_markup)
    else:
        await bot.send_message(chat_id, "🗳️ **VOTACIÓN INICIADA**\n\n⏰ Tienen 30 segundos para votar en la encuesta de arriba.")
        await bot.send_message(chat_id, "⚡ Admin puede terminar la votación inmediatamente:", reply_markup=reply_markup)
    
    # Programar auto-terminación de votación después de 1 minuto
    # La votación se terminará manualmente o por tiempo en el callback

async def end_voting_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback para terminar votación inmediatamente"""
    query = update.callback_query
    chat_id = query.message.chat_id
    user = query.from_user
    
    await query.answer()
    
    if not await is_admin(context.bot, chat_id, user.id):
        await query.edit_message_text("❌ Solo los administradores pueden terminar la votación.")
        return
    
    if chat_id not in active_games:
        await query.edit_message_text("❌ No hay juego activo.")
        return
    
    game = active_games[chat_id]
    if game.state != "voting":
        await query.edit_message_text("❌ No hay votación activa.")
        return
    
    await query.edit_message_text("🗺️ **Votación terminada por el admin**")
    await end_voting(context.bot, chat_id, game)

async def end_voting(bot, chat_id, game):
    """Termina la votación y procesa resultados"""
    if chat_id not in active_games or game.state != "voting":
        logger.info(f"end_voting llamado pero juego no está en estado voting. Estado: {getattr(game, 'state', 'no_game')}")
        return
    
    logger.info(f"Terminando votación para chat {chat_id}")
    
    # Cambiar estado inmediatamente para evitar llamadas múltiples
    game.state = "processing_votes"
    
    # Parar la encuesta
    try:
        await bot.stop_poll(chat_id, game.voting_poll_id)
        await bot.send_message(chat_id, "⏱️ **VOTACIÓN TERMINADA**")
    except Exception as e:
        logger.warning(f"Error stopping poll: {e}")
    
    # Verificar si hay votos
    if not game.votes:
        await bot.send_message(
            chat_id,
            f"🤷 **NADIE VOTÓ**\n\n"
            f"🔄 No se elimina a nadie. Continuamos con la siguiente ronda..."
        )
        # Continuar a la siguiente ronda sin eliminar a nadie
        await asyncio.sleep(2)
        await start_round(bot, chat_id, game)
        return
    
    # Mostrar resumen de votos para debug
    logger.info(f"Votos recibidos: {game.votes}")
    logger.info(f"Orden de jugadores: {game.players_order}")
    logger.info(f"Impostores: {game.impostors}")
    
    # Procesar votos y encontrar al más votado
    most_voted_player = game.get_most_voted_player()
    
    if not most_voted_player:
        await bot.send_message(
            chat_id,
            f"🤷 **EMPATE EN VOTACIÓN**\n\n"
            f"🔄 No se elimina a nadie. Continuamos con la siguiente ronda..."
        )
        await asyncio.sleep(2)
        await start_round(bot, chat_id, game)
        return
    
    # Alguien fue votado
    player_name = game.players[most_voted_player]['name']
    vote_count = sum(1 for vote in game.votes.values() if vote == game.players_order.index(most_voted_player))
    
    if most_voted_player in game.impostors:
        # ¡Atraparon a un impostor!
        game.eliminate_player(most_voted_player)  # Eliminar del juego
        
        impostors_left = len(game.impostors)  # Impostores que quedan activos
        
        if impostors_left == 0:
            # Todos los impostores eliminados - Ciudadanos ganan
            await bot.send_message(
                chat_id,
                f"🎯 **¡IMPOSTOR ELIMINADO!**\n\n"
                f"👹 **{player_name}** era impostor ({vote_count} votos).\n\n"
                f"🏆 **¡VICTORIA DE LOS CIUDADANOS!**\n\n"
                f"🎮 **¡JUEGO TERMINADO!** Todos los impostores eliminados.\n\n"
                f"👹 Impostores eliminados: {', '.join([game.players[p]['name'] for p in game.eliminated_players if p in game.players])}\n"
                f"👤 Ciudadanos: {', '.join([game.players[p]['name'] for p in game.citizens])}",
                parse_mode='Markdown'
            )
            await end_game(chat_id)
        else:
            # Aún quedan impostores - continuar juego
            await bot.send_message(
                chat_id,
                f"🎯 **¡IMPOSTOR ELIMINADO!**\n\n"
                f"👹 **{player_name}** era impostor ({vote_count} votos).\n\n"
                f"⚠️ Aún quedan {impostors_left} impostor(es) activo(s).\n"
                f"🔄 Continuamos a la siguiente ronda...",
                parse_mode='Markdown'
            )
            
            if game.current_round >= game.max_rounds:
                # Se acabaron las rondas pero quedan impostores
                await bot.send_message(
                    chat_id,
                    f"🎮 **¡JUEGO TERMINADO!**\n\n"
                    f"🏆 **¡VICTORIA DE LOS IMPOSTORES!**\n\n"
                    f"Impostores restantes: {', '.join([game.players[p]['name'] for p in game.impostors])}",
                    parse_mode='Markdown'
                )
                await end_game(chat_id)
            else:
                await asyncio.sleep(3)
                await start_round(bot, chat_id, game)
    else:
        # No atraparon al impostor (eliminaron a un ciudadano)
        await bot.send_message(
            chat_id,
            f"❌ **IMPOSTOR NO DESCUBIERTO**\n\n"
            f"👤 **{player_name}** era ciudadano ({vote_count} votos).\n"
            f"👹 El impostor sigue entre nosotros...",
            parse_mode='Markdown'
        )
        
        if game.current_round >= game.max_rounds:
            # Juego terminado, ganan los impostores
            await bot.send_message(
                chat_id,
                f"🎮 **¡JUEGO TERMINADO!**\n\n"
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
                f"🔄 Continuamos con la siguiente ronda..."
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
    """Comando /end_meet - Termina la discusión y va a votar"""
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
        await update.message.reply_text("🗣️ **Terminando discusión por comando del admin...**")
        await start_voting(context.bot, chat_id, game)
        
        # Programar auto-terminación de votación después de 30 segundos
        if context.job_queue:
            context.job_queue.run_once(
                lambda ctx: end_voting(ctx.bot, chat_id, game), 
                30,
                data={'chat_id': chat_id, 'game': game}
            )
    else:
        await update.message.reply_text("❌ No estamos en fase de discusión.")

async def next_player_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /next-player - El jugador actual pasa al siguiente turno"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if chat_id not in active_games:
        await update.message.reply_text("❌ No hay juego activo.")
        return
    
    game = active_games[chat_id]
    
    # Solo durante las rondas de juego
    if game.state != "playing_round":
        await update.message.reply_text("❌ No estamos en una ronda de juego.")
        return
    
    # Solo el jugador actual puede usar este comando
    if user_id != game.current_player:
        await update.message.reply_text(
            f"❌ No es tu turno. Es el turno de **{game.get_current_player_name()}**.",
            parse_mode='Markdown'
        )
        return
    
    # Pasar al siguiente jugador
    game.next_player()
    
    if game.all_players_played():
        # Todos jugaron, mostrar resumen y empezar discusión
        summary = game.get_round_words_summary()
        await context.bot.send_message(chat_id, summary, parse_mode='Markdown')
        await start_discussion(context.bot, chat_id, game, context)
    else:
        # Siguiente turno
        await update.message.reply_text(
            f"✅ Turno de **{game.get_current_player_name()}**\n"
            f"💬 Solo esta persona puede escribir ahora.",
            parse_mode='Markdown'
        )

async def check_game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /check-game - Muestra el estado actual del juego"""
    chat_id = update.effective_chat.id
    
    if chat_id not in active_games:
        await update.message.reply_text("❌ No hay juego activo.")
        return
    
    game = active_games[chat_id]
    
    # Construir mensaje de estado
    status_msg = f"🎮 **ESTADO DEL JUEGO**\n\n"
    status_msg += f"🔄 Ronda: {game.current_round}/{game.max_rounds}\n"
    status_msg += f"👥 Jugadores activos: {len([p for p in game.players_order if p not in game.eliminated_players])}\n"
    
    if game.eliminated_players:
        eliminated_names = [game.players[p]['name'] for p in game.eliminated_players if p in game.players]
        status_msg += f"❌ Eliminados: {', '.join(eliminated_names)}\n"
    
    status_msg += f"\n⚙️ Estado: {game.state}\n"
    
    if game.state == "playing_round" and game.current_player:
        status_msg += f"🎯 Turno actual: **{game.get_current_player_name()}**\n"
    
    # Mostrar palabras de la ronda actual
    if game.current_round_words:
        status_msg += f"\n{game.get_round_words_summary()}"
    
    await update.message.reply_text(status_msg, parse_mode='Markdown')

async def is_admin(bot, chat_id, user_id):
    """Verifica si el usuario es administrador del grupo"""
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except Exception as e:
        logger.warning(f"Error verificando admin status para {user_id} en {chat_id}: {e}")
        # En caso de error, permitir para evitar bloqueos
        return True

async def auto_continue_game(context):
    """Auto-continúa el juego después de 3 minutos"""
    chat_id = context.job.data
    if chat_id in active_games:
        game = active_games[chat_id]
        # Solo auto-continuar si está esperando jugadores
        if game.state == "waiting_for_players" and len(game.players) >= 3:
            # Auto-continuar configurando impostores y empezando
            max_impostors = max(1, len(game.players) // 3)
            game.num_impostors = 1  # Default 1 impostor
            game.max_rounds = 3     # Default 3 rounds
            
            await context.bot.send_message(
                chat_id,
                f"⏰ **TIEMPO AGOTADO - AUTO-INICIANDO JUEGO**\n\n"
                f"👥 Jugadores: {len(game.players)}\n"
                f"👹 Impostores: 1\n"
                f"🔄 Rondas: 3"
            )
            
            await start_game_rounds(context.bot, chat_id, game)
        elif game.state == "waiting_for_players" and len(game.players) < 3:
            await context.bot.send_message(
                chat_id,
                f"⏰ **TIEMPO AGOTADO**\n\n"
                f"❌ No hay suficientes jugadores ({len(game.players)}/3 mínimo)\n"
                f"🚫 Cancelando juego..."
            )
            await end_game(chat_id)
        # Si el juego ya está en progreso, no hacer nada

async def auto_start_voting(context):
    """Auto-inicia votación después de 2 minutos"""
    chat_id = context.job.data
    if chat_id in active_games:
        game = active_games[chat_id]
        if game.state == "discussing":
            await context.bot.send_message(
                chat_id,
                "⏰ **TIEMPO DE DISCUSIÓN AGOTADO**\n\nIniciando votación automáticamente..."
            )
            await start_voting(context.bot, chat_id, game)

async def auto_start_voting(context):
    """Auto-inicia votación después de 3 minutos"""
    chat_id = context.job.data
    if chat_id in active_games:
        game = active_games[chat_id]
        # Solo iniciar votación si estamos en discusión
        if game.state == "discussing":
            await context.bot.send_message(
                chat_id,
                "⏰ **TIEMPO DE DISCUSIÓN AGOTADO**\n\nIniciando votación automáticamente..."
            )
            await start_voting(context.bot, chat_id, game)
            
            # Programar auto-terminación de votación después de 30 segundos
            if context.job_queue:
                context.job_queue.run_once(
                    lambda ctx: end_voting(ctx.bot, chat_id, game), 
                    30,
                    data={'chat_id': chat_id, 'game': game}
                )
        # Si no estamos en discusión, no hacer nada

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error(f"Exception while handling an update: {context.error}")
    logger.error(f"Update: {update}")
    
    # Intentar enviar mensaje de error al chat si es posible
    if update and hasattr(update, 'effective_chat') and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"❌ Ocurrió un error inesperado. Inténtalo de nuevo."
            )
        except:
            pass

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
    application.add_handler(CommandHandler("next_player", next_player_command))
    application.add_handler(CommandHandler("check_game", check_game_command))
    
    # Callbacks
    application.add_handler(CallbackQueryHandler(continue_game_callback, pattern="^continue_game$"))
    application.add_handler(CallbackQueryHandler(set_impostors_callback, pattern="^impostors_"))
    application.add_handler(CallbackQueryHandler(set_rounds_callback, pattern="^rounds_"))
    application.add_handler(CallbackQueryHandler(start_voting_callback, pattern="^start_voting$"))
    application.add_handler(CallbackQueryHandler(end_voting_callback, pattern="^end_voting$"))
    
    # Handlers de encuestas y mensajes
    application.add_handler(PollAnswerHandler(poll_answer_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Iniciar bot
    logger.info("Bot iniciado")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()