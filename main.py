import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# -----------------------------
# CONFIGURACIÓN BÁSICA
# -----------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "PON_AQUI_TU_TOKEN_SI_NO_USAS_ENV")

# Admin opcional: si quieres que solo tú controles el bot, pon tu ID aquí
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))  # 0 = cualquiera

# Estado del bot
origin_chat_id = None      # canal origen
dest_chat_id = None        # chat destino (grupo/canal)
topic_id = None            # ID de topic (para supergrupos con temas)
copy_active = True         # si está copiando o no
copy_mode = "all"          # all, text, photo, video

# Acciones pendientes por usuario (para configurar origen/destino/topic)
pending_action = {}        # {user_id: "set_origin"/"set_dest"/"set_topic"}


# -----------------------------
# FUNCIONES DE AYUDA
# -----------------------------
def is_admin(user_id: int) -> bool:
    if ADMIN_ID == 0:
        return True
    return user_id == ADMIN_ID


def build_panel():
    buttons = [
        [InlineKeyboardButton("Cambiar canal origen", callback_data="c_origin")],
        [InlineKeyboardButton("Cambiar chat destino", callback_data="c_dest")],
        [InlineKeyboardButton("Cambiar topic", callback_data="c_topic")],
        [InlineKeyboardButton("Activar/Desactivar copia", callback_data="toggle_copy")],
        [InlineKeyboardButton("Tipo de copia", callback_data="mode")],
        [InlineKeyboardButton("Ver estado", callback_data="status")],
    ]
    return InlineKeyboardMarkup(buttons)


def build_mode_buttons():
    buttons = [
        [InlineKeyboardButton("Solo texto", callback_data="m_text")],
        [InlineKeyboardButton("Solo fotos", callback_data="m_photo")],
        [InlineKeyboardButton("Solo videos", callback_data="m_video")],
        [InlineKeyboardButton("Todo", callback_data="m_all")],
    ]
    return InlineKeyboardMarkup(buttons)


# -----------------------------
# COMANDOS
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        "Hola, soy tu bot oficial.\n\n"
        "Copio mensajes nuevos de un canal origen hacia un chat destino.\n"
        "Usa /panel para abrir el panel de control.\n\n"
        "Asegúrate de:\n"
        "- Agregarme como administrador en el canal origen.\n"
        "- Agregarme al chat destino (grupo/canal)."
    )


async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("No tienes permiso para usar el panel.")
        return

    await update.message.reply_text(
        "Panel de control del bot:",
        reply_markup=build_panel()
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Comandos disponibles:\n"
        "/start - Información del bot\n"
        "/panel - Panel de control con botones\n"
        "/help - Esta ayuda"
    )


# -----------------------------
# CALLBACKS DE BOTONES
# -----------------------------
async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global copy_active, copy_mode, origin_chat_id, dest_chat_id, topic_id

    query = update.callback_query
    await query.answer()
    user = query.from_user

    if not is_admin(user.id):
        await query.edit_message_text("No tienes permiso para usar el panel.")
        return

    data = query.data

    if data == "c_origin":
        pending_action[user.id] = "set_origin"
        await query.edit_message_text(
            "Envíame ahora el ID del canal origen.\n\n"
            "Ejemplo: -1001234567890\n\n"
            "Puedes obtenerlo con bots tipo @userinfobot o similares."
        )

    elif data == "c_dest":
        pending_action[user.id] = "set_dest"
        await query.edit_message_text(
            "Envíame ahora el ID del chat destino (grupo/canal).\n\n"
            "Ejemplo: -1009876543210"
        )

    elif data == "c_topic":
        pending_action[user.id] = "set_topic"
        await query.edit_message_text(
            "Envíame ahora el ID del topic (solo si tu grupo tiene temas).\n\n"
            "Si no usas temas, puedes poner 0."
        )

    elif data == "toggle_copy":
        copy_active = not copy_active
        estado = "ACTIVADA" if copy_active else "DESACTIVADA"
        await query.edit_message_text(
            f"Copia ahora está: {estado}",
            reply_markup=build_panel()
        )

    elif data == "mode":
        await query.edit_message_text(
            "Selecciona el tipo de copia:",
            reply_markup=build_mode_buttons()
        )

    elif data.startswith("m_"):
        if data == "m_text":
            copy_mode = "text"
        elif data == "m_photo":
            copy_mode = "photo"
        elif data == "m_video":
            copy_mode = "video"
        elif data == "m_all":
            copy_mode = "all"

        await query.edit_message_text(
            f"Tipo de copia cambiado a: {copy_mode}",
            reply_markup=build_panel()
        )

    elif data == "status":
        await query.edit_message_text(
            "Estado actual del bot:\n\n"
            f"Origen: {origin_chat_id}\n"
            f"Destino: {dest_chat_id}\n"
            f"Topic: {topic_id}\n"
            f"Copia activa: {copy_active}\n"
            f"Modo: {copy_mode}",
            reply_markup=build_panel()
        )


# -----------------------------
# MENSAJES PARA CONFIGURAR ORIGEN/DESTINO/TOPIC
# -----------------------------
async def config_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global origin_chat_id, dest_chat_id, topic_id

    message = update.message
    user = update.effective_user

    # Ignorar comandos
    if message.text and message.text.startswith("/"):
        return

    if user.id not in pending_action:
        return

    action = pending_action.pop(user.id)
    txt = message.text.strip()

    try:
        if action == "set_origin":
            origin_chat_id = int(txt)
            await message.reply_text(f"Canal origen cambiado a: {origin_chat_id}")

        elif action == "set_dest":
            dest_chat_id = int(txt)
            await message.reply_text(f"Chat destino cambiado a: {dest_chat_id}")

        elif action == "set_topic":
            topic_id = int(txt)
            await message.reply_text(f"Topic cambiado a: {topic_id}")

    except Exception as e:
        await message.reply_text(f"Error cambiando configuración: {e}")


# -----------------------------
# COPIA EN VIVO DE MENSAJES
# -----------------------------
async def mirror(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global origin_chat_id, dest_chat_id, topic_id, copy_active, copy_mode

    message = update.message
    chat = update.effective_chat

    # Solo copiar si origen y destino están configurados
    if origin_chat_id is None or dest_chat_id is None:
        return

    # Solo copiar si viene del canal origen
    if chat.id != origin_chat_id:
        return

    # Si la copia está desactivada, no hacemos nada
    if not copy_active:
        return

    # Filtros por tipo de copia
    if copy_mode == "text" and not message.text:
        return
    if copy_mode == "photo" and not message.photo:
        return
    if copy_mode == "video" and not message.video:
        return
    # "all" no filtra nada

    try:
        if message.photo:
            await context.bot.send_photo(
                chat_id=dest_chat_id,
                photo=message.photo[-1].file_id,
                caption=message.caption or message.text or "",
                message_thread_id=topic_id if topic_id and topic_id != 0 else None,
            )
        elif message.video:
            await context.bot.send_video(
                chat_id=dest_chat_id,
                video=message.video.file_id,
                caption=message.caption or message.text or "",
                message_thread_id=topic_id if topic_id and topic_id != 0 else None,
            )
        elif message.document:
            await context.bot.send_document(
                chat_id=dest_chat_id,
                document=message.document.file_id,
                caption=message.caption or message.text or "",
                message_thread_id=topic_id if topic_id and topic_id != 0 else None,
            )
        else:
            await context.bot.send_message(
                chat_id=dest_chat_id,
                text=message.text or "",
                message_thread_id=topic_id if topic_id and topic_id != 0 else None,
            )

    except Exception as e:
        print(f"Error copiando mensaje: {e}")


# -----------------------------
# MAIN
# -----------------------------
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("panel", panel))
    app.add_handler(CommandHandler("help", help_cmd))

    app.add_handler(CallbackQueryHandler(on_button))

    # Mensajes para configurar origen/destino/topic
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT, config_message))

    # Copia en vivo (escucha todos los chats, filtra dentro)
    app.add_handler(MessageHandler(filters.ALL, mirror))

    print("Bot iniciado.")
    await app.run_polling()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
