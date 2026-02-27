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
import time
import sys

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

# Flag para evitar múltiples instancias de polling
_polling_started = False

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
    try:
        total = get_total_confessions()
        hoy = get_today_confessions()
        return f"""
        <h1>📊 Estadísticas del Bot</h1>
        <p>Total confesiones: {total}</p>
        <p>Confesiones hoy: {hoy}</p>
        """
    except:
        return "📊 Estadísticas no disponibles aún", 200

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

cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_stats (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        count_today INTEGER DEFAULT 0,
        total_confessions INTEGER DEFAULT 0,
        last_reset TEXT
    )
''')

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
    today = datetime.now().strftime('%Y-%m-%d')
    
    cursor.execute('SELECT count_today, last_reset, total_confessions FROM user_stats WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if result is None:
        cursor.execute('''
            INSERT INTO user_stats (user_id, username, count_today, total_confessions, last_reset) 
            VALUES (?, ?, 1, 1, ?)
        ''', (user_id, username, today))
        conn.commit()
        return True, 1, 6
    
    count_today, last_reset, total = result
    
    if last_reset != today:
        cursor.execute('''
            UPDATE user_stats 
            SET count_today = 1, last_reset = ?, total_confessions = total_confessions + 1 
            WHERE user_id = ?
        ''', (today, user_id))
        conn.commit()
        return True, 1, 6
    
    if count_today >= max_confessions:
        return False, count_today, 6
    
    new_count = count_today + 1
    cursor.execute('''
        UPDATE user_stats 
        SET count_today = ?, total_confessions = total_confessions + 1 
        WHERE user_id = ?
    ''', (new_count, user_id))
    conn.commit()
    
    return True, new_count, 6

def save_confession(user_id, text, conf_type):
    now = datetime.now()
    cursor.execute('''
        INSERT INTO confessions (user_id, confession_text, confession_type, date_sent, time_sent)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, text, conf_type, now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S')))
    conn.commit()

def get_total_confessions():
    cursor.execute('SELECT COUNT(*) FROM confessions')
    return cursor.fetchone()[0]

def get_today_confessions():
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('SELECT COUNT(*) FROM confessions WHERE date_sent = ?', (today,))
    return cursor.fetchone()[0]

# ============================================
# 5. INICIALIZAR EL BOT
# ============================================
bot = telebot.TeleBot(TOKEN, parse_mode="Markdown", skip_pending=True)

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

💬 **Puedes confesar:**
• Lo que sientes • Secretos • Experiencias
• Pensamientos • ¡Lo que quieras!

⚠️ **Límite:** 6 confesiones por día

🎯 **Comandos:**
/start • /help • /soporte • /stats

👇 **Escribe tu confesión ahora (mínimo 25 palabras):**
    """
    
    teclado = types.ReplyKeyboardMarkup(resize_keyboard=True)
    teclado.add(
        types.KeyboardButton("📝 Enviar Confesión"),
        types.KeyboardButton("📞 Contacto Soporte")
    )
    
    bot.send_message(message.chat.id, texto_bienvenida, reply_markup=teclado)

@bot.message_handler(commands=['help'])
def comando_help(message):
    texto_ayuda = f"""
❓ **Centro de Ayuda**

**¿Es anónimo?** ✅ Sí, tu identidad nunca se comparte.

**¿Puedo enviar fotos?** ✅ Sí, texto y fotos.

**¿Cuánto tarda?** ⏱️ Inmediatamente

**¿Límite diario?** 📊 Máximo 6 confesiones/día

📞 **Admin:** @{SOPORTE}
🤖 **Bot:** @{BOT_USERNAME}
    """
    bot.send_message(message.chat.id, texto_ayuda)

@bot.message_handler(commands=['soporte', 'contacto', 'admin'])
def comando_soporte(message):
    texto_soporte = f"""
📞 **Contacto con Soporte**

👤 **Administrador:** @{SOPORTE}

💬 **Contactar:**
1. t.me/{SOPORTE}
2. O escribe directamente

⏰ **Respuesta:** 24-48 horas

🤖 **Bot:** @{BOT_USERNAME}
    """
    
    teclado = types.InlineKeyboardMarkup()
    # ✅ FIX: URL sin espacios
    boton = types.InlineKeyboardButton(
        f"📩 Contactar a @{SOPORTE}", 
        url=f"https://t.me/{SOPORTE}"
    )
    teclado.add(boton)
    
    bot.send_message(message.chat.id, texto_soporte, reply_markup=teclado)

@bot.message_handler(commands=['stats', 'estadisticas'])
def comando_stats(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Solo para el administrador.")
        return
    
    total = get_total_confessions()
    hoy = get_today_confessions()
    
    texto_stats = f"""
📊 **Estadísticas**

📬 Total: {total}
📅 Hoy: {hoy}
👥 Activos: En tiempo real

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
    
    if message.from_user.is_bot:
        return
    
    if message.text and message.text.startswith('/'):
        return
    
    if message.text in ["📝 Enviar Confesión", "📞 Contacto Soporte"]:
        if message.text == "📞 Contacto Soporte":
            comando_soporte(message)
        return
    
    try:
        permitido, count, max_conf = check_daily_limit(user_id, username, max_confessions=6)
        
        if not permitido:
            bot.reply_to(message, 
                f"❌ **Límite alcanzado**\n\n"
                f"📊 {count}/6 confesiones hoy.\n"
                f"⏰ Vuelve mañana.\n\n💙",
                parse_mode="Markdown")
            return
        
        if message.text:
            confesion = message.text
            palabras = confesion.split()
            num_palabras = len(palabras)
            
            if num_palabras < 25:
                bot.reply_to(message,
                    f"❌ **Muy corta**\n\n"
                    f"📝 {num_palabras}/25 palabras\n"
                    f"⚠️ Faltan: {25 - num_palabras}\n\n"
                    f"💡 Cuéntanos más detalles.",
                    parse_mode="Markdown")
                return
            
            if len(confesion) > 4000:
                bot.reply_to(message, "❌ Muy larga. Máx. 4000 caracteres.")
                return
            
            save_confession(user_id, confesion, "texto")
            
            mensaje_canal = f"""
📬 **Nueva Confesión Anónima**

{confesion}

━━━━━━━━━━━━━━━━
💬 Confiesa: @{BOT_USERNAME}
🔒 Anónimo | 📊 {count}/6 hoy
            """
            
            bot.send_message(CHAT_ID, mensaje_canal)
            bot.reply_to(message, f"✅ **¡Enviada!** ({num_palabras} palabras)")
        
        elif message.photo:
            file_id = message.photo[-1].file_id
            caption = message.caption if message.caption else ""
            
            if caption:
                palabras = caption.split()
                if len(palabras) < 25:
                    bot.reply_to(message,
                        f"❌ **Descripción corta**\n\n"
                        f"📝 {len(palabras)}/25 palabras\n"
                        f"💡 Escribe más detalles.",
                        parse_mode="Markdown")
                    return
            else:
                bot.reply_to(message, 
                    "❌ **Agrega descripción de 25 palabras mínimo.**",
                    parse_mode="Markdown")
                return
            
            save_confession(user_id, caption or "Foto", "foto")
            
            bot.send_photo(
                CHAT_ID, photo=file_id,
                caption=f"📬 **Confesión Anónima**\n\n{caption}\n\n"
                        f"━━━━━━━━━━━━━━━━\n"
                        f"💬 @{BOT_USERNAME} | 🔒 Anónimo | 📊 {count}/6",
                parse_mode="Markdown"
            )
            bot.reply_to(message, "✅ **¡Foto enviada!**")
        
    except Exception as e:
        bot.reply_to(message, "❌ Error. Intenta de nuevo. /soporte")
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

# ============================================
# 8. INICIAR EL BOT CON SAFEGUARD
# ============================================
def start_polling_safe():
    """Inicia el polling con protección contra múltiples instancias"""
    global _polling_started
    
    if _polling_started:
        print("⚠️ Polling ya está iniciado, omitiendo...")
        return
    
    _polling_started = True
    print("🔄 Iniciando polling...")
    
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            print(f"📡 Intento {attempt + 1}/{max_retries} de conectar con Telegram...")
            bot.infinity_polling(
                skip_pending=True,
                long_polling_timeout=30,
                allowed_updates=telebot.util.update_types
            )
            break
        except telebot.apihelper.ApiException as e:
            if "Conflict: terminated by other getUpdates request" in str(e):
                print(f"⚠️ Error 409 - Esperando {retry_delay}s antes de reintentar...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                raise
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(retry_delay)

if __name__ == "__main__":
    # Iniciar servidor Flask para Render
    keep_alive()
    
    print("🤖" + "="*50)
    print("🤖  BOT DE CONFESIONES ANÓNIMAS")
    print(f"🤖  Bot: @{BOT_USERNAME}")
    print(f"🤖  Admin ID: {ADMIN_ID}")
    print("🤖" + "="*50)
    print("✅ Base de datos: SQLite")
    print("✅ Anti-spam: 6 confesiones/día")
    print("✅ Flask: Puerto 8080")
    print("✅ Hosting: Render.com")
    print("🔒 Modo anónimo: ACTIVADO")
    print("🤖" + "="*50)
    
    try:
        start_polling_safe()
    except KeyboardInterrupt:
        print("\n🛑 Bot detenido por usuario")
    except Exception as e:
        print(f"\n❌ Error crítico: {e}")
        sys.exit(1)
