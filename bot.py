"""
bot.py - Bot de Confesiones Anónimas para Telegram
Creado para: @Tekvoblack
Bot: @ConfesionesTekvoBot
Con sistema Anti-Spam integrado y Flask para Render
"""

import telebot
from telebot import types
from config import get_config
import sqlite3
from datetime import datetime
from flask import Flask
from threading import Thread

# ============================================
# 1. OBTENER CONFIGURACIÓN
# ============================================
config = get_config()
TOKEN = config['token']
CHAT_ID = config['chat_id']
SOPORTE = config['soporte']
ADMIN_ID = config['admin_id']

# Username del bot
BOT_USERNAME = "ConfesionesTekvoBot"

# ============================================
# 2. SERVIDOR WEB PARA RENDER (FLASK)
# ============================================
app = Flask(__name__)

@app.route('/')
def home():
    return """
    <h1>✅ Bot de Confesiones Anónimas - ONLINE</h1>
    <p>🤖 Bot: @ConfesionesTekvoBot</p>
    <p>👤 Admin: @Tekvoblack</p>
    <p>📊 Estado: Funcionando 24/7</p>
    """

@app.route('/health')
def health():
    return "OK", 200

@app.route('/stats')
def stats():
    return f"""
    <h1>📊 Estadísticas del Bot</h1>
    <p>Total confesiones: {get_total_confessions()}</p>
    <p>Confesiones hoy: {get_today_confessions()}</p>
    """

def run_server():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    server = Thread(target=run_server)
    server.daemon = True
    server.start()

# ============================================
# 3. CONFIGURAR BASE DE DATOS
# ============================================
conn = sqlite3.connect('confesiones.db', check_same_thread=False)
cursor = conn.cursor()

# Crear tabla de estadísticas de usuarios
cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_stats (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        count_today INTEGER DEFAULT 0,
        total_confessions INTEGER DEFAULT 0,
        last_reset TEXT
    )
''')

# Crear tabla de confesiones
cursor.execute('''
    CREATE TABLE IF NOT EXISTS confessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        confession_text TEXT,
        confession_type TEXT,
        date_sent TEXT,
        time_sent TEXT
    )
''')

conn.commit()

# ============================================
# 4. FUNCIONES DE BASE DE DATOS
# ============================================
def check_daily_limit(user_id, username, max_confessions=6):
    """
    Verifica si el usuario puede enviar más confesiones hoy
    Retorna: True si puede enviar, False si alcanzó el límite
    """
    today = datetime.now().strftime('%Y-%m-%d')
    
    cursor.execute('SELECT count_today, last_reset, total_confessions FROM user_stats WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if result is None:
        # Usuario nuevo - registrar
        cursor.execute('''
            INSERT INTO user_stats (user_id, username, count_today, total_confessions, last_reset) 
            VALUES (?, ?, 1, 1, ?)
        ''', (user_id, username, today))
        conn.commit()
        return True, 1, 6
    
    count_today, last_reset, total = result
    
    # Si es un nuevo día, resetear contador
    if last_reset != today:
        cursor.execute('''
            UPDATE user_stats 
            SET count_today = 1, last_reset = ?, total_confessions = total_confessions + 1 
            WHERE user_id = ?
        ''', (today, user_id))
        conn.commit()
        return True, 1, 6
    
    # Verificar límite
    if count_today >= max_confessions:
        return False, count_today, 6
    
    # Incrementar contador
    new_count = count_today + 1
    cursor.execute('''
        UPDATE user_stats 
        SET count_today = ?, total_confessions = total_confessions + 1 
        WHERE user_id = ?
    ''', (new_count, user_id))
    conn.commit()
    
    return True, new_count, 6

def save_confession(user_id, text, conf_type):
    """Guarda la confesión en la base de datos"""
    now = datetime.now()
    cursor.execute('''
        INSERT INTO confessions (user_id, confession_text, confession_type, date_sent, time_sent)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, text, conf_type, now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S')))
    conn.commit()

def get_total_confessions():
    """Obtiene el total de confesiones"""
    cursor.execute('SELECT COUNT(*) FROM confessions')
    return cursor.fetchone()[0]

def get_today_confessions():
    """Obtiene confesiones de hoy"""
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('SELECT COUNT(*) FROM confessions WHERE date_sent = ?', (today,))
    return cursor.fetchone()[0]

# ============================================
# 5. INICIALIZAR EL BOT
# ============================================
bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# ============================================
# 6. COMANDOS
# ============================================

@bot.message_handler(commands=['start'])
def comando_start(message):
    texto_bienvenida = f"""
👋 **¡Hola {message.from_user.first_name}!**

Bienvenido al **Bot de Confesiones Anónimas** 🔒

📝 **¿Cómo funciona?**
• Escribe tu confesión y envíamela
• Yo la publicaré de forma **100% anónima** en el canal
• Nadie sabrá que fuiste tú

💬 **Puedes confesar:**
• Lo que sientes
• Secretos
• Experiencias
• Pensamientos
• ¡Lo que quieras!

⚠️ **Límite:** 6 confesiones por día

🎯 **Comandos disponibles:**
/start - Iniciar el bot
/help - Ayuda
/soporte - Contactar administrador
/stats - Estadísticas del bot

👇 **Escribe tu confesión ahora (mínimo 25 palabras):**
    """
    
    teclado = types.ReplyKeyboardMarkup(resize_keyboard=True)
    boton1 = types.KeyboardButton("📝 Enviar Confesión")
    boton2 = types.KeyboardButton("📞 Contacto Soporte")
    teclado.add(boton1, boton2)
    
    bot.send_message(message.chat.id, texto_bienvenida, reply_markup=teclado)

@bot.message_handler(commands=['help'])
def comando_help(message):
    texto_ayuda = f"""
❓ **Centro de Ayuda**

📌 **Información:**

**¿Es realmente anónimo?**
✅ Sí, tu identidad nunca se comparte. El mensaje aparece como enviado por el bot.

**¿Puedo enviar fotos?**
✅ Sí, puedes enviar texto, fotos, o ambos juntos.

**¿Cuánto tarda en publicarse?**
⏱️ Inmediatamente

**¿Cuántas confesiones puedo enviar?**
📊 Máximo 6 confesiones por día

📞 **¿Necesitas ayuda?**
Usa el comando /soporte para contactar al administrador.

👤 **Administrador:** @{SOPORTE}
🤖 **Bot:** @{BOT_USERNAME}
    """
    bot.send_message(message.chat.id, texto_ayuda)

@bot.message_handler(commands=['soporte', 'contacto', 'admin'])
def comando_soporte(message):
    texto_soporte = f"""
📞 **Contacto con Soporte**

¿Tienes problemas, sugerencias o reportes?

👤 **Administrador:** @{SOPORTE}

💬 **Cómo contactar:**
1. Haz clic en el enlace: t.me/{SOPORTE}
2. O escribe directamente en Telegram

⏰ **Horario de atención:**
• Respuesta en 24-48 horas

🤖 **Bot:** @{BOT_USERNAME}
    """
    
    teclado = types.InlineKeyboardMarkup()
    boton_contacto = types.InlineKeyboardButton(
        f"📩 Contactar a @{SOPORTE}", 
        url=f"https://t.me/{SOPORTE}"
    )
    teclado.add(boton_contacto)
    
    bot.send_message(message.chat.id, texto_soporte, reply_markup=teclado)

@bot.message_handler(commands=['stats', 'estadisticas'])
def comando_stats(message):
    # Solo el admin (por ID) puede ver estadísticas
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Este comando es solo para el administrador.")
        return
    
    total = get_total_confessions()
    hoy = get_today_confessions()
    
    texto_stats = f"""
📊 **Estadísticas del Bot**

📬 **Total de confesiones:** {total}
📅 **Confesiones hoy:** {hoy}
👥 **Usuarios activos:** En tiempo real
🌐 **Canal:** Activo 24/7
👤 **Admin:** {message.from_user.first_name}

💡 **Gracias por usar nuestro bot!**

🤖 @{BOT_USERNAME}
    """
    bot.send_message(message.chat.id, texto_stats)

# ============================================
# 7. MANEJAR CONFESIONES
# ============================================

@bot.message_handler(content_types=['text', 'photo'])
def manejar_confesion(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Sin_username"
    
    # Ignorar mensajes de otros bots
    if message.from_user.is_bot:
        return
    
    # Ignorar comandos
    if message.text and message.text.startswith('/'):
        return
    
    # Ignorar botones del teclado
    if message.text in ["📝 Enviar Confesión", "📞 Contacto Soporte"]:
        if message.text == "📞 Contacto Soporte":
            comando_soporte(message)
        return
    
    try:
        # ========================================
        # VERIFICAR LÍMITE DIARIO
        # ========================================
        permitido, count, max_conf = check_daily_limit(user_id, username, max_confessions=6)
        
        if not permitido:
            bot.reply_to(
                message, 
                f"❌ **Límite diario alcanzado**\n\n"
                f"📊 Ya has enviado {count}/6 confesiones hoy.\n"
                f"⏰ Vuelve mañana para enviar más.\n\n"
                f"💡 **Consejo:** Espera hasta mañana para compartir más confesiones.\n\n"
                f"¡Gracias por participar! 💙",
                parse_mode="Markdown"
            )
            return
        
        # ========================================
        # PROCESAR TEXTO
        # ========================================
        if message.text:
            confesion = message.text
            
            # Contar palabras
            palabras = confesion.split()
            num_palabras = len(palabras)
            
            # Validar mínimo 25 palabras
            if num_palabras < 25:
                bot.reply_to(
                    message, 
                    f"❌ **Tu confesión es muy corta.**\n\n"
                    f"📝 **Palabras:** {num_palabras}/25\n"
                    f"⚠️ **Faltan:** {25 - num_palabras} palabras\n\n"
                    f"💡 **Consejo:** Cuéntanos más detalles. "
                    f"¿Qué sientes? ¿por qué? ¿cuándo ocurrió?\n\n"
                    f"👉 **Escribe al menos 25 palabras.**",
                    parse_mode="Markdown"
                )
                return
            
            # Validar máximo
            if len(confesion) > 4000:
                bot.reply_to(message, "❌ La confesión es muy larga. Máximo 4000 caracteres.")
                return
            
            # Guardar en base de datos
            save_confession(user_id, confesion, "texto")
            
            # Formatear mensaje para el canal
            mensaje_canal = f"""
📬 **Nueva Confesión Anónima**

{confesion}

━━━━━━━━━━━━━━━━
💬 ¿Quieres confesar? → @{BOT_USERNAME}
🔒 100% Anónimo | 📊 {count}/6 hoy
            """
            
            # Enviar al canal
            bot.send_message(CHAT_ID, mensaje_canal)
            
            # Confirmar al usuario
            bot.reply_to(
                message, 
                f"✅ **¡Confesión enviada con éxito!**\n\n"
                f"📝 **Palabras:** {num_palabras}\n"
                f"📊 **Tu límite:** {count}/6 confesiones hoy\n"
                f"⏰ **Publicada:** En breves momentos\n\n"
                f"¿Quieres enviar otra? ¡Escribe de nuevo!",
                parse_mode="Markdown"
            )
        
        # ========================================
        # PROCESAR FOTOS
        # ========================================
        elif message.photo:
            file_id = message.photo[-1].file_id
            caption = message.caption if message.caption else ""
            
            if caption:
                palabras = caption.split()
                num_palabras = len(palabras)
                
                # Validar mínimo 25 palabras
                if num_palabras < 25:
                    bot.reply_to(
                        message,
                        f"❌ **Descripción muy corta.**\n\n"
                        f"📝 **Palabras:** {num_palabras}/25\n"
                        f"⚠️ **Faltan:** {25 - num_palabras} palabras\n\n"
                        f"💡 **Escribe más detalles sobre tu foto.**",
                        parse_mode="Markdown"
                    )
                    return
            else:
                bot.reply_to(
                    message, 
                    "❌ **Las fotos deben incluir descripción.**\n\n"
                    "📝 **Requisito:** Mínimo 25 palabras explicando la foto.\n\n"
                    "💡 **Ejemplo:** 'Esta foto me recuerda cuando...' y cuenta tu historia.",
                    parse_mode="Markdown"
                )
                return
            
            # Guardar en base de datos
            save_confession(user_id, caption or "Foto sin texto", "foto")
            
            # Enviar foto al canal
            bot.send_photo(
                CHAT_ID, 
                photo=file_id, 
                caption=f"📬 **Confesión Anónima**\n\n{caption}\n\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"💬 Confiesa: @{BOT_USERNAME}\n"
                        f"🔒 Anónimo | 📊 {count}/6 hoy",
                parse_mode="Markdown"
            )
            
            # Confirmar al usuario
            bot.reply_to(
                message, 
                f"✅ **¡Foto enviada con éxito!**\n\n"
                f"📊 **Tu límite:** {count}/6 confesiones hoy\n"
                f"Se publicará en el canal.",
                parse_mode="Markdown"
            )
        
    except Exception as e:
        bot.reply_to(
            message, 
            "❌ Hubo un error al enviar tu confesión.\n\n"
            "Por favor intenta de nuevo en unos minutos.\n\n"
            "Si el problema persiste: /soporte"
        )
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

# ============================================
# 8. INICIAR EL BOT
# ============================================
if __name__ == "__main__":
    # Iniciar servidor web para Render (IMPORTANTE)
    keep_alive()
    
    print("🤖" + "="*50)
    print("🤖  BOT DE CONFESIONES ANÓNIMAS")
    print("🤖  Bot: @ConfesionesTekvoBot")
    print("🤖  Creado para: @Tekvoblack")
    print("🤖  Admin ID: " + str(ADMIN_ID))
    print("🤖" + "="*50)
    print("✅ Base de datos: SQLite (confesiones.db)")
    print("✅ Anti-spam: 6 confesiones/día")
    print("✅ Servidor Flask: PUERTO 8080")
    print("✅ Bot iniciado correctamente...")
    print("📡 Escaneando nuevos mensajes...")
    print("🔒 Modo anónimo: ACTIVADO")
    print("🌐 Hosting: Render.com")
    print("🤖" + "="*50)
    
    bot.infinity_polling()
