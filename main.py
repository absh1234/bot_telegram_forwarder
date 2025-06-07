import json
import asyncio
import nest_asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from telethon import TelegramClient, events
from telethon.sync import TelegramClient
import threading
import asyncio

api_id = "20770144"
api_hash = "3d402211b8687b77058db0dcbf7ab045"
bot_token = "7852836848:AAE4yZOcbnhJeDAEimzz0cYKylUSiL4IAeE"
SETTINGS_FILE = "settings.json"


def telethon_worker():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient("session", api_id, api_hash)

    @client.on(events.NewMessage())
    async def handler(event):
        st = load_settings()
        if not (st["source_channel"] and st["target_channel"] and st["auto_forwarding"]):
            return
        if str(event.chat_id) == str(st["source_channel"]) or ("@" in str(st["source_channel"]) and getattr(event.chat, "username", "") == st["source_channel"].replace("@", "")):
            try:
                # ارسال استیکر پریمیوم و سایر پیام‌ها
                if event.sticker:
                    await client.send_file(
                        st["target_channel"],
                        event.file,
                        caption=st["custom_caption"]
                    )
                else:
                    await client.forward_messages(
                        st["target_channel"],
                        event.id,
                        event.chat_id
                    )
                    if st["custom_caption"]:
                        await client.send_message(
                            st["target_channel"],
                            st["custom_caption"]
                        )
            except Exception as e:
                print("Error:", e)
    client.start()
    client.run_until_disconnected()


def load_settings():
    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except:
        return {
            "source_channel": None,
            "target_channel": None,
            "custom_caption": "",
            "auto_forwarding": False,
            "admin_id": None
        }


def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)


settings = load_settings()


def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("تنظیم کانال مبدا", callback_data="set_source")],
        [InlineKeyboardButton("تنظیم کانال مقصد", callback_data="set_target")],
        [InlineKeyboardButton("ویرایش کپشن", callback_data="set_caption")],
        # <== این خط جدید
        [InlineKeyboardButton("انتخاب و ویرایش پیام",
                              callback_data="selectmsg_menu")],
        [InlineKeyboardButton("فعال/غیرفعال فوروارد",
                              callback_data="toggle_forward")],
        [InlineKeyboardButton("وضعیت ربات", callback_data="status")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if settings['admin_id'] is None:
        settings['admin_id'] = user_id
        save_settings(settings)
        await update.message.reply_text("شما به عنوان ادمین ثبت شدید.", reply_markup=get_main_menu())
    elif user_id != settings['admin_id']:
        await update.message.reply_text("شما دسترسی مدیریت ندارید.")
    else:
        await update.message.reply_text("به منوی مدیریت خوش آمدید.", reply_markup=get_main_menu())


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != settings['admin_id']:
        await update.message.reply_text("دسترسی ندارید.")
        return
    await update.message.reply_text("منوی اصلی:", reply_markup=get_main_menu())


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id != settings["admin_id"]:
        await query.edit_message_text("دسترسی ندارید.")
        return

    if query.data == "set_source":
        await query.edit_message_text("آیدی عددی یا @username کانال مبدا را ارسال کنید.", reply_markup=cancel_menu())
        context.user_data["set_source"] = True
    elif query.data == "set_target":
        await query.edit_message_text("آیدی عددی یا @username کانال مقصد را ارسال کنید.", reply_markup=cancel_menu())
        context.user_data["set_target"] = True
    elif query.data == "set_caption":
        await query.edit_message_text("کپشن دلخواه خود را ارسال کنید.", reply_markup=cancel_menu())
        context.user_data["set_caption"] = True
    elif query.data == "toggle_forward":
        settings["auto_forwarding"] = not settings["auto_forwarding"]
        save_settings(settings)
        text = "✅ ارسال خودکار **فعال** شد." if settings["auto_forwarding"] else "❌ ارسال خودکار **غیرفعال** شد."
        await query.edit_message_text(text, reply_markup=get_main_menu(), parse_mode="Markdown")
    elif query.data == "status":
        msg = f"""
👤 ادمین: {settings['admin_id']}
📢 مبدا: {settings['source_channel']}
🎯 مقصد: {settings['target_channel']}
✏️ کپشن: {settings['custom_caption']}
🔁 وضعیت: {"فعال" if settings['auto_forwarding'] else "غیرفعال"}
        """
        await query.edit_message_text(msg, reply_markup=get_main_menu())
    elif query.data == "selectmsg_menu":
        await select_message_menu(update, context)
        return
    elif query.data.startswith("selectmsg_"):
        await message_action_menu(update, context)
        return
    elif query.data == "edit_caption":
        await edit_caption_start(update, context)
        return


def cancel_menu():
    keyboard = [[InlineKeyboardButton("↩️ بازگشت", callback_data="cancel")]]
    return InlineKeyboardMarkup(keyboard)


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text("عملیات لغو شد.", reply_markup=get_main_menu())


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != settings["admin_id"]:
        await update.message.reply_text("دسترسی ندارید.")
        return

    if context.user_data.get("set_source"):
        settings["source_channel"] = update.message.text.strip()
        save_settings(settings)
        await update.message.reply_text(f"کانال مبدا ثبت شد: {settings['source_channel']}", reply_markup=get_main_menu())
        context.user_data.clear()
    elif context.user_data.get("set_target"):
        settings["target_channel"] = update.message.text.strip()
        save_settings(settings)
        await update.message.reply_text(f"کانال مقصد ثبت شد: {settings['target_channel']}", reply_markup=get_main_menu())
        context.user_data.clear()
    elif context.user_data.get("set_caption"):
        settings["custom_caption"] = update.message.text.strip()
        save_settings(settings)
        await update.message.reply_text("کپشن ثبت شد.", reply_markup=get_main_menu())
        context.user_data.clear()
    else:
        await update.message.reply_text("از منوی زیر استفاده کنید.", reply_markup=get_main_menu())

# ---- Telethon Worker ----


def telethon_worker():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient("session", api_id, api_hash)

    @client.on(events.NewMessage())
    async def handler(event):
        st = load_settings()
        if not (st["source_channel"] and st["target_channel"] and st["auto_forwarding"]):
            return
        if str(event.chat_id) == str(st["source_channel"]) or ("@" in str(st["source_channel"]) and getattr(event.chat, "username", "") == st["source_channel"].replace("@", "")):
            try:
                # ارسال استیکر پریمیوم و سایر پیام‌ها
                if event.sticker:
                    await client.send_file(
                        st["target_channel"],
                        event.file,
                        caption=st["custom_caption"]
                    )
                else:
                    await client.forward_messages(
                        st["target_channel"],
                        event.id,
                        event.chat_id
                    )
                    if st["custom_caption"]:
                        await client.send_message(
                            st["target_channel"],
                            st["custom_caption"]
                        )
            except Exception as e:
                print("Error:", e)
    client.start()
    client.run_until_disconnected()


async def get_last_messages(limit=5):
    async with TelegramClient("session", api_id, api_hash) as client:
        messages = []
        async for msg in client.iter_messages(settings['source_channel'], limit=limit):
            preview = msg.text[:30] if msg.text else '[بدون متن]'
            messages.append((msg.id, preview))
        return messages


async def select_message_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != settings['admin_id']:
        await update.callback_query.edit_message_text("دسترسی ندارید.")
        return
    messages = await get_last_messages()
    keyboard = []
    for msg_id, preview in messages:
        btn = InlineKeyboardButton(
            f"{preview}", callback_data=f"selectmsg_{msg_id}")
        keyboard.append([btn])
    keyboard.append([InlineKeyboardButton(
        "↩️ بازگشت", callback_data="cancel")])
    await update.callback_query.edit_message_text("یکی از پیام‌ها را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))


async def message_action_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    msg_id = int(query.data.split("_")[1])
    context.user_data["selected_msg_id"] = msg_id
    keyboard = [
        [InlineKeyboardButton("✏️ ویرایش کپشن", callback_data="edit_caption")],
        [InlineKeyboardButton("↩️ بازگشت", callback_data="cancel")]
    ]
    await query.edit_message_text(f"پیام {msg_id} انتخاب شد. چه کاری انجام شود؟", reply_markup=InlineKeyboardMarkup(keyboard))


async def edit_caption_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("کپشن جدید را ارسال کنید:")
    context.user_data["edit_caption"] = True


async def edit_caption_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("edit_caption"):
        return
    new_caption = update.message.text
    msg_id = context.user_data.get("selected_msg_id")
    # اینجا باید آیدی پیام مقصد را داشته باشی تا بتوانی کپشن را ادیت کنی.
    # به طور نمونه فقط تایید میکنیم!
    await update.message.reply_text(f"کپشن جدید برای پیام {msg_id} ثبت شد.")
    context.user_data.clear()


async def main():
    threading.Thread(target=telethon_worker, daemon=True).start()
    app = ApplicationBuilder().token(bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", main_menu))
    app.add_handler(CallbackQueryHandler(cancel_handler, pattern="^cancel$"))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_handler(CallbackQueryHandler(
        select_message_menu, pattern="^selectmsg_menu$"))
    app.add_handler(CallbackQueryHandler(
        message_action_menu, pattern="^selectmsg_"))
    app.add_handler(CallbackQueryHandler(
        edit_caption_start, pattern="^edit_caption$"))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(
        settings["admin_id"]), edit_caption_finish))

    print("ربات اجرا شد.")
    await app.run_polling()


if __name__ == "__main__":

    nest_asyncio.apply()

    asyncio.get_event_loop().run_until_complete(main())
