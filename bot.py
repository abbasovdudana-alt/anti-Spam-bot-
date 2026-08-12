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
        "• Tag (@username) və ya Reply ilə idarəetmə\n"
        "• Sonsuz və ya vaxtlı `/mute` / `/unmute`\n"
        "• `/ban`, `/unban`, `/warn`, `/unwarn` sistemləri\n\n"
        "🛠 **Qurucu / Owner:** @sasaadminn\n"
        "🚀 **Versiya:** PRO v5.2"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

def parse_time(time_str):
    if not time_str:
        return 0  # 0 demək sonsuz deməkdir
    unit = time_str[-1].lower()
    try:
        value = int(time_str[:-1])
    except ValueError:
        return 0

    if unit == 's': return value
    elif unit == 'm': return value * 60
    elif unit == 'h': return value * 3600
    elif unit == 'd': return value * 86400
    return 0

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.message.from_user
    chat = update.effective_chat
    
    member = await chat.get_member(user.id)
    if member.status in ['creator', 'administrator']:
        return True
    
    await update.message.reply_text("⚠️ Bu komutdan yalnız **qrup adminləri** istifadə edə bilər!", parse_mode="Markdown")
    return False

# Hədəfi tapmaq üçün köməkçi funksiya (Reply və ya @tag dəstəyi)
async def get_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    # 1. Əgər mesaja cavab (reply) verilibsə
    if message.reply_to_message:
        return message.reply_to_message.from_user, []
    
    # 2. Əgər komutla birlikdə @tag yazılıbsa (məsələn: /mute @test 10m)
    if context.args:
        first_arg = context.args[0]
        if first_arg.startswith("@"):
            username = first_arg[1:]
            chat_id = message.chat.id
            try:
                # Qrupdakı üzvlərdən tapmağa çalışırıq (Telegram API birbaşa username ilə axtarmadığı üçün entity yoxlanılır)
                for entity in message.entities:
                    if entity.type == "text_mention":
                        return entity.user, context.args[1:]
                    elif entity.type == "mention":
                        # Əgər sadəcə @username text olaraq yazılıbsa
                        # Bot sahibinin qrupdakı üzvü tapması üçün əlavə sorğu tələb oluna bilər
                        pass
            except Exception:
                pass
            
            # Əgər textmention tapılmadısa, sadəcə argümanları ötürürük
            # Alternativ olaraq text-dəki username-i parse etmək lazımdır
    return None, context.args

# MUTE KOMUTU (Sonsuz və ya vaxtlı, Tag və ya Reply dəstəkli)
async def manual_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    message = update.message
    chat_id = message.chat.id

    target_user = None
    time_arg = None

    # Reply edilibsə
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        if context.args:
            time_arg = context.args[0]
    # @tag yazılibsə (məsələn: /mute @user 10m)
    elif context.args and message.entities:
        for entity in message.entities:
            if entity.type == "text_mention":
                target_user = entity.user
                break
            elif entity.type == "mention" and len(context.args) > 0:
                # Username vasitəsilə tag edilibsə
                username_str = message.text[entity.offset : entity.offset + entity.length]
                # Qeyd: Telegram API username ilə birbaşa user object vermədiyi üçün mesajdakı mention-u yoxlayırıq
                pass

    # Əgər hələ də tapılmayıbsa, sadəcə mətn içindən user tapmağa çalışaq
    if not target_user and message.reply_to_message:
        target_user = message.reply_to_message.from_user
    
    if not target_user:
        await message.reply_text("⚠️ Zəhmət olmasa istifadəçini **tag edin (@ad)** və ya **mesajına cavab verin**!\n_Məsələn: /mute @username 10m və ya sadəcə /mute_", parse_mode="Markdown")
        return

    target_mention = f"[{target_user.first_name}](tg://user?id={target_user.id})"

    try:
        target_member = await context.bot.get_chat_member(chat_id, target_user.id)
        if target_member.status in ['creator', 'administrator']:
            await message.reply_text("❌ **Olmaz!** Admini və ya qrup sahibini mute edə bilməzsən!", parse_mode="Markdown")
            return
    except Exception:
        pass

    duration = parse_time(time_arg) if time_arg else 0
    mute_until = int(time.time() + duration) if duration > 0 else 0
    duration_text = time_arg if time_arg else "Sonsuz (Admin açana qədər)"

    try:
        await context.bot.restrict_chat_member(
            chat_id, target_user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=mute_until
        )
        success_msg = (
            "╭━ 🔇 **İSTİFADƏÇİ MUTE EDİLDİ** 🔇 ━╮\n\n"
            f"👤 **İstifadəçi:** {target_mention}\n"
            f"⏱ **Müddət:** `{duration_text}`\n"
            "📜 **Status:** Mesaj yazmaq hüququ məhdudlaşdırıldı.\n\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
        )
        await message.reply_text(success_msg, parse_mode="Markdown")
    except Exception as e:
        await message.reply_text(f"❌ Xəta baş verdi: {e}")

# UNMUTE KOMUTU
async def manual_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
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
                can_send_audios=True,
                can_send_documents=True,
                can_send_photos=True,
                can_send_videos=True,
                can_send_video_notes=True,
                can_send_voice_notes=True,
                can_send_polls=True,
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

# BAN KOMUTU (Reply və ya Text Mention dəstəkli)
async def manual_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    message = update.message
    chat_id = message.chat.id
    
    target_user = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif message.entities:
        for entity in message.entities:
            if entity.type == "text_mention":
                target_user = entity.user
                break

    if not target_user:
        await message.reply_text("⚠️ Zəhmət olmasa banlamaq istədiyiniz şəxsin **mesajına cavab verin** və ya **tag edin (@ad)**!", parse_mode="Markdown")
        return

    target_mention = f"[{target_user.first_name}](tg://user?id={target_user.id})"

    try:
        target_member = await context.bot.get_chat_member(chat_id, target_user.id)
        if target_member.status in ['creator', 'administrator']:
            await message.reply_text("❌ **Olmaz!** Admini və ya qrup sahibini qrupdan ban edə bilməzsən!", parse_mode="Markdown")
            return
    except Exception:
        pass

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

# UNBAN KOMUTU
async def manual_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
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

# WARN KOMUTU
async def manual_warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    message = update.message
    chat_id = message.chat.id
    
    target_user = None
    reason_args = []

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        reason_args = context.args
    elif message.entities:
        for entity in message.entities:
            if entity.type == "text_mention":
                target_user = entity.user
                # Tag-dən sonrakı hissəni səbəb kimi götürürük
                reason_args = context.args[1:]
                break

    if not target_user:
        await message.reply_text("⚠️ Zəhmət olmasa xəbərdarlıq vermək istədiyiniz şəxsin **mesajına cavab verin** və ya **tag edin (@ad)**!\n_Məsələn: /warn @user səbəb_", parse_mode="Markdown")
        return

    target_mention = f"[{target_user.first_name}](tg://user?id={target_user.id})"
    
    try:
        target_member = await context.bot.get_chat_member(chat_id, target_user.id)
        if target_member.status in ['creator', 'administrator']:
            await message.reply_text("❌ **Olmaz!** Adminə xəbərdarlıq vermək olmaz!", parse_mode="Markdown")
            return
    except Exception:
        pass

    reason = " ".join(reason_args) if reason_args else "Göstərilməyib"
    user_key = f"{chat_id}_{target_user.id}"
    
    if user_key not in warnings_db:
        warnings_db[user_key] = []
        
    warnings_db[user_key].append(reason)
    current_warns = len(warnings_db[user_key])

    if current_warns >= 3:
        try:
            await context.bot.ban_chat_member(chat_id, target_user.id)
            warnings_db[user_key] = []
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
            f"📜 **Səbəb:** `{reason}`\n\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
        )
        await message.reply_text(warn_msg, parse_mode="Markdown")

# UNWARN KOMUTU
async def manual_unwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    message = update.message
    chat_id = message.chat.id
    
    target_user = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif message.entities:
        for entity in message.entities:
            if entity.type == "text_mention":
                target_user = entity.user
                break

    if not target_user:
        await message.reply_text("⚠️ Zəhmət olmasa xəbərdarlığını silmək istədiyiniz şəxsin **mesajına cavab verin** və ya **tag edin (@ad)**!", parse_mode="Markdown")
        return

    target_mention = f"[{target_user.first_name}](tg://user?id={target_user.id})"
    user_key = f"{chat_id}_{target_user.id}"
    
    if user_key in warnings_db and len(warnings_db[user_key]) > 0:
        warnings_db[user_key].pop()
        current_warns = len(warnings_db[user_key])
        unwarn_msg = (
            "╭━ ✅ **XƏBƏRDARLIQ SİLİNDİ** ✅ ━╮\n\n"
            f"👤 **İstifadəçi:** {target_mention}\n"
            f"📊 **Qalan xəbərdarlıq:** `{current_warns} / 3`\n\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
        )
        await message.reply_text(unwarn_msg, parse_mode="Markdown")
    else:
        await message.reply_text("ℹ️ Bu istifadəçinin aktiv xəbərdarlığı yoxdur.", parse_mode="Markdown")

# ANTİ-SPAM VƏ FLOOD
async def anti_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    
    message = update.message
    user = message.from_user
    chat_id = update.effective_chat.id
    user_mention = f"[{user.first_name}](tg://user?id={user.id})"

    try:
        member = await context.bot.get_chat_member(chat_id, user.id)
        if member.status in ['creator', 'administrator']:
            return
    except Exception:
        pass

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
    app.add_handler(CommandHandler("mute", manual_mute))
    app.add_handler(CommandHandler("unmute", manual_unmute))
    app.add_handler(CommandHandler("ban", manual_ban))
    app.add_handler(CommandHandler("unban", manual_unban))
    app.add_handler(CommandHandler("warn", manual_warn))
    app.add_handler(CommandHandler("unwarn", manual_unwarn))
    
    app.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), anti_spam))
    
    print("Bot PRO v5.2 işə düşdü...")
    app.run_polling()

if __name__ == '__main__':
    main()
