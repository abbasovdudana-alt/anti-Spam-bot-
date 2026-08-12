import logging
import time
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

SPAM_WORDS = ["t.me/", "http://", "https://", "mərc", "kazino", "bonus", "kripto", "qazananc", "investisiya"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🛡 **Anti-Spam & Flood Botuna Xoş Gəlmisiniz!**\n\n"
        "Mən qrupunuzu reklamçılardan, zərərli linklərdən, spam mesajlardan və sürətli mesaj yazanlardan (flood) qorumaq üçün yaradılmış güclü sisteməm.\n\n"
        "⚙️ **Botun İmkanları:**\n"
        "• Linklərin avtomatik silinməsi\n"
        "• Qadağan olunmuş sözlərin bloklanması\n"
        "• 5 saniyədə 5-dən çox mesaj yazanlara 1 dəqiqəlik MUTE\n"
        "• İstifadəçilərə xəbərdarlıq göndərilməsi\n\n"
        "🛠 **Qurucu / Owner:** @sasaadminn\n"
        "🚀 **Versiya:** PRO v4.4\n\n"
        "📌 *Qeyd: Botun tam işləməsi üçün onu qrupa əlavə edib mesajları silmək və üzvləri məhdudlaşdırmaq səlahiyyəti ilə Admin etməlisiniz!*"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def anti_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return

    user = update.message.from_user
    chat_id = update.effective_chat.id
    user_mention = f"[{user.first_name}](tg://user?id={user.id})"

    # Sınaq üçün admin yoxlamasını müvəqqəti ləğv edirik ki, özündə yoxlaya biləsən 
    # (Qeyd: Telegram qrup sahibini heç bir botun mute etməsinə icazə verməz, adi admini edə bilər)

    # FLOOD Yoxlaması (Timestamp əsaslı)
    now = time.time()
    if 'last_msgs' not in context.user_data: context.user_data['last_msgs'] = []
    
    # Son 5 saniyəlik mesajları saxla
    context.user_data['last_msgs'] = [t for t in context.user_data['last_msgs'] if now - t < 5]
    context.user_data['last_msgs'].append(now)

    # Əgər 5 saniyə içində mesaj sayı 5-ə çatsa
    if len(context.user_data['last_msgs']) >= 5:
        context.user_data['last_msgs'] = [] # Sayğacı dərhal sıfırla ki, təkrar işləməsin
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
                "📜 **Səbəb:** Çox sürətli mesaj yazmaq.\n\n"
                "╰━━━━━━━━━━━━━━━━━━╯"
            )
            await update.message.reply_text(mute_msg, parse_mode="Markdown")
        except Exception as e: 
            print(f"Mute xətası (Böyük ehtimalla admin/owner hədəf alındı): {e}")
        return

    # Spam söz yoxlaması
    if any(word in update.message.text.lower() for word in SPAM_WORDS):
        try:
            await update.message.delete()
            spam_msg = (
                "╭━ ⚠️ **REKLAM / SPAM AŞKARLANDI!** ⚠️ ━╮\n\n"
                f"👤 **İstifadəçi:** {user_mention}\n"
                "🗑 **Status:** Mesajınız silindi!\n"
                "╰━━━━━━━━━━━━━━━━━━━━━━━╯"
            )
            await context.bot.send_message(chat_id=chat_id, text=spam_msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Spam xətası: {e}")

def main():
    TOKEN = "8687802391:AAG9xMvo5RlnCWrRfSpogDpVYCeeJf0G5LI"
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), anti_spam))
    print("Bot PRO v4.4 işə düşdü...")
    app.run_polling()

if __name__ == '__main__':
    main()
