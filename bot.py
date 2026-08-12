import logging
import time
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

SPAM_WORDS = ["t.me/", "http://", "https://", "mərc", "kazino", "bonus", "kripto", "qazananc", "investisiya"]

warnings_db = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🛡 **Anti-Spam & Moderasiya Botuna Xoş Gəlmisiniz!**\n\n"
        "Mən qrupunuzu reklamçılardan, zərərli linklərdən, stiker/mesaj floodlarından və qayda pozanlardan qoruyuram.\n\n"
        "⚙️ **Botun İmkanları:**\n"
        "• Linklərin və Mesajların idarəsi\n"
        "• Qadağan olunmuş sözlərin bloklanması\n"
        "• Sürətli mesajlara avtomatik Mute\n"
        "• `/warn` (3 xəbərdarlıqda avto-ban)\n"
        "• `/mute` və `/unmute` komutları\n"
        "• `/ban` və `/unban` komutları\n\n"
        "🛠 **Qurucu / Owner:** @sasaadminn\n"
        "🚀 **Versiya:** PRO v4.8"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

def parse_time(time_str):
    if not time_str:
        return 60
    unit = time_str[-1].lower()
    try:
        value = int(time_str[:-1])
    except ValueError:
        return 60

    if unit == 's': return value
    elif unit == 'm': return value * 60
    elif unit == 'h': return value * 3600
    elif unit == 'd': return value * 86400
    return 60

# MUTE KOMUTU
async def manual_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message.reply_to_message:
        await message.reply_text("⚠️ Zəhmət olmasa səssizləşdirmək istədiyiniz şəxsin **mesajına cavab verərək** bu komutu işlədin!\n_Məsələn: /mute 10m_", parse_mode="Markdown")
        return

    chat_id = message.chat.id
    target_user = message.reply_to_message.from_user
    target_mention = f"[{target_user.first_name}](tg://user?id={target_user.id})"
    
    time_arg = context.args[0] if context.args else "1m"
    duration = parse_time(time_arg)
    mute_until = int(time.time() + duration)

    try:
        await context.bot.restrict_chat_member(
            chat_id, target_user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=mute_until
        )
        success_msg = (
            "╭━ 🔇 **İSTİFADƏÇİ MUTE EDİLDİ** 🔇 ━╮\n\n"
            f"👤 **İstifadəçi:** {target_mention}\n"
            f"⏱ **Müddət:** `{time_arg}`\n"
            "📜 **Status:** Mesaj yazmaq hüququ məhdudlaşdırıldı.\n\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
        )
        await message.reply_text(success_msg, parse_mode="Markdown")
    except Exception as e:
        await message.reply_text(f"❌ Xəta baş verdi: {e}")

# UNMUTE KOMUTU
async def manual_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message.reply_to_message:
        await message.reply_text("⚠️ Zəhmət olmasa səssizliyini qaldırmaq istədiyiniz şəxsin **mesajına cavab verərək** `/unmute` yazın!", parse_mode="Markdown")
        return

    chat_id = message.chat.id
    target_user = message.reply_to_message.from_user
    target_mention = f"[{target_user.first_name}](tg://user?id={target_user.id})"

    try:
        await context.bot.restrict_chat_member(
            chat_id, target_user.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
        unmute_msg = (
            "╭━ 🔊 **MUTE QALDIRILDI** 🔊 ━╮\n\n"
            f"👤 **İstifadəçi:** {target_mention}\n"
            "📜 **Status:** Yenidən mesaj yazmaq hüququ verildi.\n\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
        )
        await message.reply_text(unmute_msg, parse_mode="Markdown")
    except Exception as e:
        await message.reply_text(f"❌ Xəta baş verdi: {e}")

# BAN KOMUTU
async def manual_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message.reply_to_message:
        await message.reply_text("⚠️ Zəhmət olmasa banlamaq istədiyiniz şəxsin **mesajına cavab verərək** `/ban` yazın!", parse_mode="Markdown")
        return

    chat_id = message.chat.id
    target_user = message.reply_to_message.from_user
    target_mention = f"[{target_user.first_name}](tg://user?id={target_user.id})"

    try:
        await context.bot.ban_chat_member(chat_id, target_user.id)
        ban_msg = (
            "╭━ 🔨 **İSTİFADƏÇİ BAN OLUNDU** 🔨 ━╮\n\n"
            f"👤 **İstifadəçi:** {target_mention}\n"
            "🗑 **Status:** Qrupdan qovuldu və geri gələ bilməz!\n\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
        )
        await message.reply_text(ban_msg, parse_mode="Markdown")
    except Exception as e:
        await message.reply_text(f"❌ Xəta baş verdi: {e}")

# UNBAN KOMUTU (/unban <user_id>)
async def manual_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not context.args:
        await message.reply_text("⚠️ Zəhmət olmasa istifadəçinin **ID nömrəsini** qeyd edin!\n_Məsələn: /unban 123456789_", parse_mode="Markdown")
        return

    chat_id = message.chat.id
    try:
        user_id = int(context.args[0])
        await context.bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
        
        unban_msg = (
            "╭━ 🔓 **BAN QALDIRILDI** 🔓 ━╮\n\n"
            f"👤 **İstifadəçi ID:** `{user_id}`\n"
            "📜 **Status:** Qrupdan ban qaldırıldı, yenidən qoşula bilər.\n\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
        )
        await message.reply_text(unban_msg, parse_mode="Markdown")
    except Exception as e:
        await message.reply_text(f"❌ Xəta baş verdi (ID-ni düzgün yazdığınızdan əmin olun): {e}")

# WARN (XƏBƏRDARLIQ) KOMUTU
async def manual_warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message.reply_to_message:
        await message.reply_text("⚠️ Zəhmət olmasa xəbərdarlıq vermək istədiyiniz şəxsin **mesajına cavab verərək** `/warn` yazın!", parse_mode="Markdown")
        return

    chat_id = message.chat.id
    target_user = message.reply_to_message.from_user
    target_mention = f"[{target_user.first_name}](tg://user?id={target_user.id})"
    
    user_key = f"{chat_id}_{target_user.id}"
    warnings_db[user_key] = warnings_db.get(user_key, 0) + 1
    current_warns = warnings_db[user_key]

    if current_warns >= 3:
        try:
            await context.bot.ban_chat_member(chat_id, target_user.id)
            warnings_db[user_key] = 0
            ban_msg = (
                "╭━ 🚨 **LİMİT AŞILDI (3/3 BAN)** 🚨 ━╮\n\n"
                f"👤 **İstifadəçi:** {target_mention}\n"
                "⚠️ 3 dəfə xəbərdarlıq aldığı üçün qrupdan **ban olundu**!\n\n"
                "╰━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
            )
            await message.reply_text(ban_msg, parse_mode="Markdown")
        except Exception as e:
            await message.reply_text(f"❌ Ban xətası: {e}")
    else:
        warn_msg = (
            "╭━ ⚠️ **XƏBƏRDARLIQ VERİLDİ** ⚠️ ━╮\n\n"
            f"👤 **İstifadəçi:** {target_mention}\n"
            f"📊 **Xəbərdarlıq sayı:** `{current_warns} / 3`\n"
            "📜 *Qeyd: 3 xəbərdarlıq avtomatik ban ilə nəticələnəcək!*\n\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
        )
        await message.reply_text(warn_msg, parse_mode="Markdown")

# ANTİ-SPAM VƏ FLOOD
async def anti_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    
    message = update.message
    user = message.from_user
    chat_id = update.effective_chat.id
    user_mention = f"[{user.first_name}](tg://user?id={user.id})"

    now = time.time()
    if 'last_msgs' not in context.user_data: context.user_data['last_msgs'] = []
    
    context.user_data['last_msgs'] = [t for t in context.user_data['last_msgs'] if now - t < 5]
    context.user_data['last_msgs'].append(now)

    if len(context.user_data['last_msgs']) >= 5:
        context.user_data['last_msgs'] = [] 
        try:
            mute_until = int(time.time() + 60)
            await context.bot.restrict_chat_member(
                chat_id, user.id, 
                permissions=ChatPermissions(can_send_messages=False),
                until_date=mute_until
            )
            mute_msg = (
                "╭━ 🚫 **FLOOD TƏHLÜKƏSİ!** 🚫 ━╮\n\n"
                f"👤 **İstifadəçi:** {user_mention}\n"
                "⏱ **Məhdudiyyət:** `1 Dəqiqəlik Mute`\n"
                "📜 **Səbəb:** Çox sürətli mesaj göndərmək.\n\n"
                "╰━━━━━━━━━━━━━━━━━━╯"
            )
            await message.reply_text(mute_msg, parse_mode="Markdown")
        except Exception as e: 
            print(f"Mute xətası: {e}")
        return

    if message.text and any(word in message.text.lower() for word in SPAM_WORDS):
        try:
            await message.delete()
            spam_msg = (
                "╭━ ⚠️ **REKLAM / SPAM AŞKARLANDI!** ⚠️ ━╮\n\n"
                f"👤 **İstifadəçi:** {target_mention if 'target_mention' in locals() else 'İstifadəçi'}\n"
                "🗑 **Status:** Mesajınız silindi!\n"
                "╰━━━━━━━━━━━━━━━━━━━━━━━╯"
            )
            await context.bot.send_message(chat_id=chat_id, text=spam_msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Spam xətası: {e}")

def main():
    TOKEN = "8687802391:AAG9xMvo5RlnCWrRfSpogDpVYCeeJf0G5LI"
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Bütün komandalar
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mute", manual_mute))
    app.add_handler(CommandHandler("unmute", manual_unmute))
    app.add_handler(CommandHandler("ban", manual_ban))
    app.add_handler(CommandHandler("unban", manual_unban))
    app.add_handler(CommandHandler("warn", manual_warn))
    
    app.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), anti_spam))
    
    print("Bot PRO v4.8 işə düşdü...")
    app.run_polling()

if __name__ == '__main__':
    main()
