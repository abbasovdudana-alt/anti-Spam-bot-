import logging
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, ChatMemberHandler, filters

logging.basicConfig(level=logging.INFO)

# Qrup ayarları üçün sadə yaddaş
group_settings = {}
warnings_db = {}

WELCOME_TEMPLATE = (
    "•          𝐖𝐄𝐋𝐂𝐎𝐌𝐄 𝐂𝐇𝐀𝐓 🔝🇦🇿    •\n\n"
    "Aramıza Xoş Gəldin !\n"
    "Burda Hərşey Sərbəstdir😍\n\n"
    "𝙽𝚊𝚖𝚎 : {name}\n"
    "𝚄𝚜𝚎𝚛𝚗𝚊𝚖𝚎 : {username}\n"
    "𝙸𝙳 : {id}\n\n"
    "Gif Stiker Medya Sərbəst✅\n\n"
    "Söyüş Reklam Flood Qadağandır⛔️"
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛡 **Anti-Spam & Moderasiya Botu (PRO v9.0)**\n\n"
        "İdarəetmə:\n"
        "/mute @user /ban @user /warn @user\n"
        "/unmute @user /unban ID\n"
        "/welcome [on/off] /setwelcome [mətn]"
    )

async def get_user_from_msg(update, context):
    msg = update.message
    if msg.reply_to_message:
        return msg.reply_to_message.from_user
    if context.args:
        query = context.args[0].replace("@", "")
        # Qrup üzvlərini axtarırıq
        try:
            # Əgər qrupda mesaj yazıbsa, cache-dən və ya axtarışla tapmaq daha rahatdır
            chat_id = msg.chat.id
            admins = await context.bot.get_chat_administrators(chat_id)
            for admin in admins:
                if admin.user.username and admin.user.username.lower() == query.lower():
                    return admin.user
        except: pass
    return None

async def mute(update, context):
    user = await get_user_from_msg(update, context)
    if not user: return await update.message.reply_text("İstifadəçi tapılmadı.")
    await context.bot.restrict_chat_member(update.message.chat.id, user.id, ChatPermissions(can_send_messages=False))
    await update.message.reply_text(f"🔇 {user.first_name} sessizə alındı.")

async def unmute(update, context):
    user = await get_user_from_msg(update, context)
    if not user: return await update.message.reply_text("İstifadəçi tapılmadı.")
    
    member = await context.bot.get_chat_member(update.message.chat.id, user.id)
    if member.can_send_messages:
        await update.message.reply_text("ℹ️ Bu istifadəçi onsuz da danışa bilir.")
    else:
        await context.bot.restrict_chat_member(update.message.chat.id, user.id, ChatPermissions(can_send_messages=True))
        await update.message.reply_text(f"🔊 {user.first_name} sessizdən çıxarıldı.")

async def welcome_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_member = update.chat_member.new_chat_member
    if new_member.status == "member":
        user = new_member.user
        username = f"@{user.username}" if user.username else "Yoxdur"
        text = WELCOME_TEMPLATE.format(name=user.first_name, username=username, id=user.id)
        await context.bot.send_message(update.effective_chat.id, text)

def main():
    app = ApplicationBuilder().token("8687802391:AAG9xMvo5RlnCWrRfSpogDpVYCeeJf0G5LI").build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))
    app.add_handler(ChatMemberHandler(welcome_member, ChatMemberHandler.CHAT_MEMBER))
    
    print("Bot PRO v9.0 aktivdir.")
    app.run_polling()

if __name__ == '__main__':
    main()
