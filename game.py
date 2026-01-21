"""
Lógica del juego Impostor para Telegram
Maneja estados, jugadores, turnos y votaciones
"""

import random
from typing import Dict, List, Optional
from words import get_random_word

class ImpostorGame:
    def __init__(self, chat_id: int):
        self.chat_id = chat_id
        self.players: Dict[int, Dict] = {}  # {user_id: {'name': str, 'role': str}}
        self.state = "waiting_for_players"  # Estados del juego
        
        # Configuración del juego
        self.num_impostors = 1
        self.max_rounds = 3
        self.current_round = 0
        
        # Roles y palabras
        self.current_word = ""
        self.impostors: List[int] = []
        self.citizens: List[int] = []
        
        # Control de turnos
        self.current_player_index = 0
        self.current_player = None
        self.players_order: List[int] = []
        self.players_played_this_round: List[int] = []
        self.eliminated_players: List[int] = []  # Jugadores eliminados durante el juego
        
        # Seguimiento de palabras dichas por ronda
        self.round_words: Dict[int, List[Dict]] = {}  # {round_num: [{'player_id': int, 'player_name': str, 'word': str}]}
        self.current_round_words: List[Dict] = []  # Palabras de la ronda actual
        self.current_player_last_message: Optional[str] = None  # Último mensaje del jugador actual
        
        # Votación
        self.votes: Dict[int, int] = {}  # {voter_id: voted_player_index}
        self.poll_message_id = None
        self.voting_poll_id = None
    
    def add_player(self, user_id: int, name: str):
        """Agrega un jugador al juego"""
        if user_id not in self.players:
            self.players[user_id] = {
                'name': name,
                'role': None
            }
    
    def remove_player(self, user_id: int):
        """Remueve un jugador del juego"""
        if user_id in self.players:
            del self.players[user_id]
    
    def assign_roles(self):
        """Asigna roles aleatoriamente y selecciona palabra"""
        if len(self.players) < 3:
            raise ValueError("Se necesitan al menos 3 jugadores")
        
        # Mejorar aleatoriedad
        player_ids = list(self.players.keys())
        random.shuffle(player_ids)
        random.shuffle(player_ids)  # Doble shuffle para mayor aleatoriedad
        
        # Seleccionar impostores
        self.impostors = player_ids[:self.num_impostors]
        self.citizens = player_ids[self.num_impostors:]
        
        # Asignar roles a los jugadores
        for player_id in self.impostors:
            self.players[player_id]['role'] = 'impostor'
        
        for player_id in self.citizens:
            self.players[player_id]['role'] = 'citizen'
        
        # Seleccionar palabra aleatoria
        self.current_word = get_random_word()
        
        # Establecer orden de juego con mayor aleatoriedad
        self.players_order = player_ids.copy()
        random.shuffle(self.players_order)
        random.shuffle(self.players_order)  # Doble shuffle
        
        self.state = "playing_round"
    
    def start_new_round(self):
        """Inicia una nueva ronda"""
        # Guardar palabras de la ronda anterior si existían
        if self.current_round > 0 and self.current_round_words:
            self.round_words[self.current_round] = self.current_round_words.copy()
        
        self.current_round += 1
        self.current_round_words = []  # Limpiar palabras para nueva ronda
        self.current_player_index = 0
        
        # Filtrar jugadores eliminados del orden
        self.players_order = [p for p in self.players_order if p not in self.eliminated_players]
        
        self.current_player = self.players_order[0] if self.players_order else None
        self.players_played_this_round.clear()
        self.state = "playing_round"
    
    def add_word(self, player_id: int, word: str):
        """Registra una palabra dicha por un jugador"""
        if player_id in self.players:
            self.current_round_words.append({
                'player_id': player_id,
                'player_name': self.players[player_id]['name'],
                'word': word
            })
    
    def set_current_player_message(self, message: str):
        """Almacena temporalmente el último mensaje del jugador actual"""
        self.current_player_last_message = message
    
    def save_current_player_word(self):
        """Guarda la última palabra/frase del jugador actual cuando avanza de turno"""
        if self.current_player_last_message and self.current_player_index is not None:
            current_player_id = self.players_order[self.current_player_index]
            self.add_word(current_player_id, self.current_player_last_message)
            self.current_player_last_message = None
    
    def get_round_words_summary(self, round_num: int = None) -> str:
        """Obtiene un resumen de las palabras dichas en una ronda"""
        if round_num is None:
            round_num = self.current_round
        
        if round_num == self.current_round and self.current_round_words:
            words = self.current_round_words
        elif round_num in self.round_words:
            words = self.round_words[round_num]
        else:
            return f"📝 No hay palabras registradas para la ronda {round_num}"
        
        if not words:
            return f"📝 No hay palabras registradas para la ronda {round_num}"
        
        summary = f"📝 PALABRAS - RONDA {round_num}\n\n"
        for entry in words:
            summary += f"• {entry['player_name']}: {entry['word']}\n"
        return summary
    
    def eliminate_player(self, player_id: int):
        """Elimina un jugador del juego"""
        if player_id not in self.eliminated_players:
            self.eliminated_players.append(player_id)
            # Remover de impostores si estaba ahí
            if player_id in self.impostors:
                self.impostors.remove(player_id)
    
    def next_player(self):
        """Pasa al siguiente jugador"""
        if self.current_player:
            self.players_played_this_round.append(self.current_player)
        
        # Avanzar al siguiente jugador que no esté eliminado
        self.current_player_index += 1
        while self.current_player_index < len(self.players_order):
            potential_player = self.players_order[self.current_player_index]
            if potential_player not in self.eliminated_players:
                self.current_player = potential_player
                return
            self.current_player_index += 1
        
        self.current_player = None
    
    def all_players_played(self) -> bool:
        """Verifica si todos los jugadores activos ya jugaron en esta ronda"""
        active_players = [p for p in self.players_order if p not in self.eliminated_players]
        return len(self.players_played_this_round) >= len(active_players)
    
    def get_current_player_name(self) -> str:
        """Obtiene el nombre del jugador actual"""
        if self.current_player and self.current_player in self.players:
            return self.players[self.current_player]['name']
        return "Desconocido"
    
    def add_vote(self, voter_id: int, voted_player_index: int):
        """Registra un voto"""
        if 0 <= voted_player_index < len(self.players_order):
            self.votes[voter_id] = voted_player_index
    
    def get_most_voted_player(self) -> Optional[int]:
        """Obtiene el jugador más votado"""
        if not self.votes:
            return None
        
        # Contar votos por índice de jugador
        vote_count = {}
        for voted_index in self.votes.values():
            if voted_index in vote_count:
                vote_count[voted_index] += 1
            else:
                vote_count[voted_index] = 1
        
        # Encontrar el índice más votado
        max_votes = max(vote_count.values())
        most_voted_indices = [idx for idx, votes in vote_count.items() if votes == max_votes]
        
        # Si hay empate, retornar None
        if len(most_voted_indices) > 1:
            return None
        
        most_voted_index = most_voted_indices[0]
        
        # Retornar el ID del jugador
        if most_voted_index < len(self.players_order):
            return self.players_order[most_voted_index]
        
        return None
    
    def is_game_finished(self) -> bool:
        """Verifica si el juego ha terminado"""
        return self.current_round >= self.max_rounds
    
    def get_impostors_names(self) -> List[str]:
        """Obtiene los nombres de los impostores"""
        return [self.players[impostor_id]['name'] for impostor_id in self.impostors]
    
    def get_citizens_names(self) -> List[str]:
        """Obtiene los nombres de los ciudadanos"""
        return [self.players[citizen_id]['name'] for citizen_id in self.citizens]
    
    def get_game_summary(self) -> str:
        """Obtiene un resumen del estado del juego"""
        return (
            f"🎮 **Estado del Juego**\n"
            f"👥 Jugadores: {len(self.players)}\n"
            f"👹 Impostores: {len(self.impostors)}\n"
            f"👤 Ciudadanos: {len(self.citizens)}\n"
            f"🔄 Ronda: {self.current_round}/{self.max_rounds}\n"
            f"📝 Palabra: {self.current_word}\n"
            f"⚙️ Estado: {self.state}"
        )
    
    def reset_game(self):
        """Reinicia el juego manteniendo los jugadores"""
        self.current_round = 0
        self.current_player_index = 0
        self.current_player = None
        self.players_played_this_round.clear()
        self.votes.clear()
        self.impostors.clear()
        self.citizens.clear()
        self.current_word = ""
        self.state = "waiting_for_players"
        
        # Limpiar roles de jugadores
        for player_id in self.players:
            self.players[player_id]['role'] = None
    
    def get_player_count_by_role(self) -> tuple:
        """Retorna (num_impostores, num_ciudadanos)"""
        return len(self.impostors), len(self.citizens)
    
    def is_player_impostor(self, player_id: int) -> bool:
        """Verifica si un jugador es impostor"""
        return player_id in self.impostors
    
    def is_player_citizen(self, player_id: int) -> bool:
        """Verifica si un jugador es ciudadano"""
        return player_id in self.citizens
    
    def get_remaining_players(self) -> List[str]:
        """Obtiene la lista de jugadores que aún no han jugado en la ronda"""
        remaining = []
        for player_id in self.players_order:
            if player_id not in self.players_played_this_round:
                remaining.append(self.players[player_id]['name'])
        return remaining
    
    def validate_game_settings(self) -> tuple:
        """Valida las configuraciones del juego. Retorna (is_valid, error_message)"""
        if len(self.players) < 3:
            return False, "Se necesitan al menos 3 jugadores"
        
        if self.num_impostors >= len(self.players):
            return False, "El número de impostores debe ser menor al total de jugadores"
        
        if self.num_impostors < 1:
            return False, "Debe haber al menos 1 impostor"
        
        # Verificar que no haya demasiados impostores (máximo 1/3 del total)
        max_impostors = max(1, len(self.players) // 3)
        if self.num_impostors > max_impostors:
            return False, f"Demasiados impostores. Máximo recomendado: {max_impostors}"
        
        if self.max_rounds < 2 or self.max_rounds > 5:
            return False, "El número de rondas debe estar entre 2 y 5"
        
        return True, "Configuración válida"
    
    def get_vote_summary(self) -> str:
        """Obtiene un resumen de los votos"""
        if not self.votes:
            return "📊 **No hay votos registrados**"
        
        vote_count = {}
        for voted_index in self.votes.values():
            if voted_index in vote_count:
                vote_count[voted_index] += 1
            else:
                vote_count[voted_index] = 1
        
        summary = "📊 **Resumen de Votos:**\n"
        for player_index, votes in vote_count.items():
            if player_index < len(self.players_order):
                player_id = self.players_order[player_index]
                player_name = self.players[player_id]['name']
                summary += f"• {player_name}: {votes} voto(s)\n"
        
        return summary