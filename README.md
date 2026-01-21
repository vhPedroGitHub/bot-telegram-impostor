# 🎭 Bot de Telegram - Juego del Impostor

Un bot de Telegram para administrar grupos y jugar al juego del Impostor, donde algunos jugadores son impostores que no conocen la palabra secreta, mientras que otros son ciudadanos que sí la conocen.

## 📋 Descripción del Juego

### 🎯 Objetivo
- **Ciudadanos**: Descubrir quiénes son los impostores votándolos fuera del juego
- **Impostores**: No ser descubiertos y actuar como si conocieran la palabra secreta

### 🎮 Mecánica del Juego
1. Los jugadores se unen al juego mediante una encuesta
2. Se asignan roles aleatoriamente (impostores vs ciudadanos)
3. Los ciudadanos reciben la palabra secreta por mensaje privado
4. Los impostores reciben un mensaje indicando que son impostores
5. En cada ronda, cada jugador dice una palabra por turno
6. Si alguien dice la palabra exacta, los impostores ganan
7. Al final de cada ronda, todos votan para eliminar a un impostor
8. El juego continúa hasta que se eliminen todos los impostores o se agoten las rondas

## 🚀 Instalación y Configuración

### 📋 Requisitos Previos
- Python 3.8 o superior
- Una cuenta de Telegram
- Token de bot de Telegram (obtenido de @BotFather)

### 📦 Instalación

1. **Clonar o descargar el proyecto:**
```bash
git clone <url-del-repositorio>
cd bot-telegram-impostor
```

2. **Instalar dependencias:**
```bash
pip install -r requirements.txt
```

3. **Configurar variables de entorno:**
```bash
# Copiar el archivo de ejemplo
cp .env.example .env

# Editar el archivo .env y agregar tu token
nano .env
```

Edita el archivo `.env` y agrega tu token:
```env
BOT_TOKEN=tu_token_aqui
```

### 🤖 Crear el Bot en Telegram

1. **Hablar con @BotFather:**
   - Ir a [@BotFather](https://t.me/BotFather) en Telegram
   - Enviar `/newbot`
   - Elegir un nombre para tu bot (ej: "Mi Bot Impostor")
   - Elegir un username único (ej: "mi_bot_impostor_bot")
   - Copiar el token proporcionado

2. **Configurar el bot:**
   - Enviar `/setprivacy` a @BotFather
   - Seleccionar tu bot
   - Enviar `Disable` para que el bot pueda leer todos los mensajes del grupo

3. **Configuraciones adicionales (opcional):**
```bash
# Establecer descripción
/setdescription
Bot para jugar al Impostor en grupos de Telegram

# Establecer comandos
/setcommands
start - Iniciar un nuevo juego
cancel - Cancelar el juego actual
end_meet - Terminar discusión y votar
check_game - Ver estado del juego
next_player - Pasar turno
```

## 🏃‍♂️ Ejecución

### 🖥️ Ejecutar en tu computadora
```bash
python bot.py
```

### 🐳 Ejecutar con Docker (opcional)

1. **Crear Dockerfile:**
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "bot.py"]
```

2. **Ejecutar:**
```bash
docker build -t impostor-bot .
docker run -d --name impostor-bot -e BOT_TOKEN=tu_token_aqui impostor-bot
```

### ☁️ Despliegue en la Nube

#### Heroku
1. **Instalar Heroku CLI y crear app:**
```bash
heroku create tu-app-impostor
heroku config:set BOT_TOKEN=tu_token_aqui
```

2. **Crear Procfile:**
```
worker: python bot.py
```

3. **Desplegar:**
```bash
git add .
git commit -m "Deploy impostor bot"
git push heroku main
heroku ps:scale worker=1
```

#### Railway
1. Conectar tu repositorio a Railway
2. Agregar variable de entorno `BOT_TOKEN`
3. Deploy automático

#### VPS/Servidor Propio
```bash
# Instalar dependencias del sistema
sudo apt update
sudo apt install python3 python3-pip git

# Clonar y configurar
git clone <tu-repositorio>
cd bot-telegram-impostor
pip3 install -r requirements.txt

# Crear archivo .env con tu token
echo "BOT_TOKEN=tu_token_aqui" > .env

# Ejecutar con screen o tmux
screen -S impostor-bot
python3 bot.py
# Ctrl+A, D para separar la sesión

# O usar systemd para servicio permanente
sudo nano /etc/systemd/system/impostor-bot.service
```

**Archivo de servicio systemd:**
```ini
[Unit]
Description=Impostor Telegram Bot
After=network.target

[Service]
Type=simple
User=tu_usuario
WorkingDirectory=/ruta/a/bot-telegram-impostor
Environment=BOT_TOKEN=tu_token_aqui
ExecStart=/usr/bin/python3 bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable impostor-bot
sudo systemctl start impostor-bot
```

## 🎮 Cómo Usar el Bot

### 🏗️ Configuración Inicial
1. **Agregar el bot al grupo:**
   - Agregar tu bot al grupo de Telegram
   - Darle permisos de administrador (o asegurarte de que pueda leer mensajes)

2. **Asegurarse de que los usuarios puedan recibir mensajes privados:**
   - Cada jugador debe enviar `/start` al bot en privado antes del juego
   - Esto permite al bot enviar los roles por mensaje privado

### 🎲 Comandos del Bot

#### Para Administradores:
- **`/start`**: Inicia un nuevo juego del impostor
- **`/cancel`**: Cancela el juego actual
- **`/end_meet`**: Termina la fase de discusión y pasa a votar

### 📖 Flujo del Juego

1. **📢 Inicio del Juego:**
   ```
   Admin: /start
   ```
   - Aparece una encuesta para unirse al juego
   - Los jugadores votan "Sí" para participar
   - Duración: 3 minutos o hasta que admin presione "Continuar"

2. **⚙️ Configuración:**
   - Admin selecciona número de impostores
   - Admin selecciona número de rondas (2-5)

3. **🎭 Asignación de Roles:**
   - Bot asigna roles aleatoriamente
   - Envía palabra secreta a ciudadanos por privado
   - Envía mensaje "IMPOSTOR AHORA!!!!" a impostores

4. **🗣️ Rondas de Juego:**
   - Cada jugador dice una palabra por turno
   - Solo el jugador actual puede escribir
   - Si alguien dice la palabra exacta → Impostores ganan
   - Todos los jugadores juegan → Fase de discusión

5. **💭 Discusión:**
   - Todos pueden hablar por 2 minutos
   - Admin puede usar `/end_meet` para pasar a votar

6. **🗳️ Votación:**
   - Encuesta para votar al impostor sospechoso
   - Duración: 1 minuto o hasta que admin presione "Siguiente"
   - Si eliminan a un impostor → Ciudadanos ganan esa ronda
   - Si no → Continúa a siguiente ronda o impostores ganan

### 🏆 Condiciones de Victoria

#### 🔵 Ciudadanos Ganan:
- Eliminan a todos los impostores mediante votación
- Identifican correctamente a un impostor

#### 🔴 Impostores Ganan:
- Alguien dice la palabra secreta durante el juego
- Completan todas las rondas sin ser descubiertos
- No son eliminados por votación

## 📁 Estructura del Proyecto

```
bot-telegram-impostor/
├── bot.py              # Archivo principal del bot
├── game.py             # Lógica del juego
├── words.py            # Base de datos de palabras
├── config.py           # Configuraciones del bot
├── requirements.txt    # Dependencias de Python
├── .env.example        # Ejemplo de variables de entorno
├── .env               # Variables de entorno (crear)
├── README.md          # Esta documentación
└── .gitignore         # Archivos a ignorar en git
```

## ⚙️ Configuración Avanzada

### 📝 Personalizar Palabras
Edita el archivo [`words.py`](words.py) para agregar más categorías o palabras:

```python
WORDS_CATEGORIES = {
    "Tu_Categoria": [
        "palabra1", "palabra2", "palabra3"
    ]
}
```

### ⏰ Ajustar Tiempos
Modifica los tiempos en [`config.py`](config.py):

```python
POLL_DURATION = 180      # 3 minutos para unirse
DISCUSSION_DURATION = 120 # 2 minutos de discusión
VOTE_DURATION = 60       # 1 minuto para votar
ROLE_REVEAL_DELAY = 10   # 10 segundos para ver roles
```

### 💬 Personalizar Mensajes
Cambia los mensajes en [`config.py`](config.py):

```python
MSG_IMPOSTOR = "🎭 ¡Tu mensaje personalizado para impostores!"
MSG_CITIZEN = "👤 Tu mensaje personalizado para ciudadanos\n\nPalabra: {word}"
```

## 🐛 Solución de Problemas

### ❌ Error: "Bot token not found"
- Verifica que el archivo `.env` existe y contiene `BOT_TOKEN=tu_token`
- Asegúrate de que el token es correcto y válido

### ❌ Los jugadores no reciben mensajes privados
- Cada jugador debe enviar `/start` al bot en privado ANTES del juego
- El bot necesita poder enviar mensajes privados

### ❌ El bot no responde a comandos
- Verifica que el bot tiene permisos para leer mensajes en el grupo
- Configura el bot con @BotFather usando `/setprivacy` → Disable

### ❌ "Solo administradores pueden usar comandos"
- El usuario debe ser administrador del grupo
- Verificar permisos de administrador en el grupo

### 🔍 Logs y Debug
Para ver logs detallados:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📄 Licencia

Este proyecto es de código abierto. Siéntete libre de modificarlo y distribuirlo.

## 🤝 Contribuir

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear un Pull Request

## 📞 Soporte

Si tienes problemas o preguntas:
1. Revisa esta documentación
2. Verifica la configuración del bot
3. Consulta los logs para errores específicos
4. Crea un issue en el repositorio con detalles del problema

---

¡Disfruta jugando al Impostor con tus amigos! 🎭🎮