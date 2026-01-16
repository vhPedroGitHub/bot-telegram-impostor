"""
Lista exhaustiva de palabras para el juego del Impostor
"""
import random

# Lista de palabras categorizadas
WORDS_CATEGORIES = {
    "Animales": [
        "perro", "gato", "elefante", "jirafa", "león", "tigre", "oso", "lobo",
        "zorro", "conejo", "ratón", "ballena", "delfín", "tiburón", "cocodrilo",
        "serpiente", "águila", "búho", "loro", "pingüino", "canguro", "koala",
        "panda", "mono", "gorila", "hipopótamo", "rinoceronte", "cebra", "caballo",
        "vaca", "cerdo", "oveja", "gallina", "pato", "pavo", "ardilla", "erizo",
        "murciélago", "tortuga", "camaleón", "salamandra", "rana", "mariposa",
        "abeja", "hormiga", "araña", "escorpión", "cangrejo", "pulpo", "medusa"
    ],
    
    "Comida": [
        "pizza", "hamburguesa", "pasta", "arroz", "pan", "queso", "leche",
        "yogurt", "mantequilla", "huevo", "pollo", "carne", "pescado", "jamón",
        "salchicha", "tocino", "ensalada", "sopa", "sandwich", "taco", "burrito",
        "sushi", "ramen", "curry", "paella", "tortilla", "empanada", "arepa",
        "tamales", "ceviche", "chocolate", "helado", "pastel", "galleta", "donut",
        "manzana", "naranja", "plátano", "fresa", "uva", "sandía", "melón",
        "piña", "mango", "pera", "durazno", "cereza", "limón", "aguacate",
        "tomate", "lechuga", "zanahoria", "papa", "cebolla", "ajo", "pepino"
    ],
    
    "Objetos": [
        "mesa", "silla", "cama", "sofá", "lámpara", "espejo", "reloj", "teléfono",
        "computadora", "televisor", "radio", "cámara", "libro", "lápiz", "pluma",
        "cuaderno", "mochila", "maleta", "paraguas", "gafas", "sombrero", "zapato",
        "camisa", "pantalón", "vestido", "chaqueta", "calcetín", "guante", "bufanda",
        "reloj", "collar", "anillo", "pulsera", "llave", "candado", "cuchillo",
        "tenedor", "cuchara", "plato", "vaso", "taza", "botella", "olla", "sartén",
        "refrigerador", "estufa", "lavadora", "aspiradora", "martillo", "destornillador"
    ],
    
    "Profesiones": [
        "médico", "enfermero", "dentista", "veterinario", "maestro", "profesor",
        "ingeniero", "arquitecto", "abogado", "juez", "policía", "bombero",
        "soldado", "piloto", "marinero", "chef", "cocinero", "mesero", "barista",
        "carpintero", "plomero", "electricista", "mecánico", "pintor", "jardinero",
        "agricultor", "pescador", "minero", "artista", "músico", "cantante",
        "actor", "bailarín", "escritor", "periodista", "fotógrafo", "diseñador",
        "programador", "científico", "biólogo", "químico", "físico", "astrónomo",
        "veterano", "deportista", "entrenador", "árbitro", "contador", "banquero"
    ],
    
    "Lugares": [
        "casa", "apartamento", "edificio", "escuela", "universidad", "hospital",
        "farmacia", "supermercado", "tienda", "restaurante", "café", "bar",
        "hotel", "aeropuerto", "estación", "museo", "teatro", "cine", "parque",
        "playa", "montaña", "bosque", "desierto", "río", "lago", "océano",
        "isla", "ciudad", "pueblo", "país", "continente", "iglesia", "templo",
        "mezquita", "biblioteca", "banco", "oficina", "fábrica", "almacén",
        "mercado", "plaza", "estadio", "gimnasio", "piscina", "zoológico",
        "acuario", "circo", "castillo", "puente", "torre"
    ],
    
    "Deportes": [
        "fútbol", "baloncesto", "voleibol", "tenis", "béisbol", "golf", "rugby",
        "hockey", "cricket", "natación", "atletismo", "gimnasia", "boxeo",
        "lucha", "judo", "karate", "taekwondo", "esgrima", "ciclismo", "motociclismo",
        "automovilismo", "esquí", "snowboard", "surf", "buceo", "vela", "remo",
        "escalada", "paracaidismo", "equitación", "polo", "bowling", "billar",
        "dardos", "tiro", "arquería", "patinaje", "skateboarding", "parkour"
    ],
    
    "Transportes": [
        "coche", "automóvil", "camión", "autobús", "motocicleta", "bicicleta",
        "tren", "metro", "tranvía", "avión", "helicóptero", "barco", "yate",
        "lancha", "submarino", "ferry", "canoa", "kayak", "velero", "crucero",
        "cohete", "nave", "globo", "teleférico", "funicular", "monopatín",
        "patineta", "patines", "trineo", "carreta", "carruaje", "ambulancia",
        "taxi", "limosina", "scooter", "segway"
    ],
    
    "Naturaleza": [
        "árbol", "flor", "rosa", "tulipán", "girasol", "margarita", "orquídea",
        "hierba", "césped", "arbusto", "cactus", "palmera", "pino", "roble",
        "sauce", "nube", "lluvia", "nieve", "granizo", "trueno", "rayo", "viento",
        "huracán", "tornado", "terremoto", "volcán", "avalancha", "inundación",
        "sequía", "eclipse", "arcoíris", "aurora", "estrella", "luna", "sol",
        "planeta", "cometa", "meteoro", "galaxia", "nebulosa", "montaña", "colina",
        "valle", "cañón", "cueva", "acantilado", "cascada", "río"
    ],
    
    "Tecnología": [
        "smartphone", "tablet", "laptop", "ordenador", "monitor", "teclado",
        "ratón", "impresora", "escáner", "router", "módem", "disco", "memoria",
        "procesador", "tarjeta", "cable", "cargador", "batería", "auriculares",
        "altavoz", "micrófono", "webcam", "proyector", "consola", "videojuego",
        "drone", "robot", "inteligencia", "bluetooth", "wifi", "internet",
        "correo", "mensaje", "aplicación", "programa", "software", "hardware",
        "servidor", "nube", "algoritmo", "código"
    ],
    
    "Emociones": [
        "felicidad", "alegría", "tristeza", "enojo", "miedo", "sorpresa",
        "disgusto", "amor", "odio", "vergüenza", "culpa", "orgullo", "celos",
        "envidia", "gratitud", "esperanza", "ansiedad", "nerviosismo", "calma",
        "paz", "euforia", "melancolía", "nostalgia", "aburrimiento", "frustración",
        "confusión", "curiosidad", "admiración", "desprecio", "compasión"
    ]
}

def get_all_words():
    """Obtiene todas las palabras de todas las categorías"""
    all_words = []
    for category, words in WORDS_CATEGORIES.items():
        all_words.extend(words)
    return all_words

def get_random_word():
    """Obtiene una palabra aleatoria de todas las categorías"""
    all_words = get_all_words()
    return random.choice(all_words)

def get_random_word_from_category(category):
    """Obtiene una palabra aleatoria de una categoría específica"""
    if category in WORDS_CATEGORIES:
        return random.choice(WORDS_CATEGORIES[category])
    return get_random_word()
