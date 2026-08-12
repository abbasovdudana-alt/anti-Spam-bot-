import logging
import time
from telegram import Update, ChatPermissions, ChatMemberUpdated
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, ChatMemberHandler, filters

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

SPAM_WORDS = ["t.me/", "http://", "https://", "mərc", "kazino", "bonus", "kripto", "qazananc", "investisiya"]

warnings_db = {}
group_settings = {}

DEFAULT_WELCOME_TEXT = (
    "•          𝐖𝐄𝐋𝐂𝐎𝐌𝐄 𝐂𝐇𝐀𝐓 🔝🇦🇿    •\n\n"
    "Aramıza Xoş Gəldin, {user_mention} !\n"
    "Burda Hərşey Sərbəstdir 😍\n\n"
    "𝙽𝚊𝚖𝚎 : {user_name}\n"
    "𝚄𝚜𝚎𝚛𝚗𝚊𝚖𝚎 : {user_username}\n"
    "𝙸𝙳 : {user_id}\n\n"
    "Gif Stiker Medya Sərbəst ✅\n\n"
    "Söyüş Reklam Flood Qadağandır ⛔️\n\n"
    "🌍 Qrupumuza qoşulduğunuz üçün şadıq!\n"
    "Burada hörmət, səmimiyyət və xoş ünsiyyət əsasdır. 🤝\n"
    "📌 Qrup qaydalarına riayət edin.\n"
    "💬 Söhbətlərdə aktiv olun və xoş vaxt keçirin! ❤️\n\n"
    "👑 **Kurucu:** @YerKuresinde\n"
    "🛡️ **Nəzarət:** @sasaadminn"
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🛡 **Anti-Spam & Moderasiya Botuna Xoş Gəlmisiniz!**\n\n"
        "Mən qrupunuzu reklamçılardan, zərərli linklərdən, stiker/mesaj floodlarından və qayda pozanlardan qoruyuram.\n\n"
        "⚙️ **İdarəetmə Komutları:**\n"
        "• `/mute [@user] [vaxt]` (Məsələn: `/mute @salamqaqa 10m` və ya sadəcə `/mute` sonsuz)\n"
        "• `/unmute [@user]`\n"
        "• `/ban [@user]`\n"
        "• `/unban [user_id]`\n"
        "• `/warn [@user] [səbəb]`\n"
        "• `/unwarn [@user]`\n"
        "• `/welcome on / off` | `/setwelcome [mətn]`\n\n"
        "🛠 **Qurucu / Owner:** @sasaadminn\n"
        "🚀 **Versiya:** PRO v8.0"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

def parse_time(time_str):
    if not time_str:
        return 0
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
    await update.message.reply_text("⚠️ **Diqqət:** Bu əmrdən yalnız qrup adminləri istifadə edə bilər!", parse_mode="Markdown")
    return False

# Tag (@username) və ya Reply ilə istifadəçini tam dəqiq tapan təkmilləşdirilmiş sistem
async def resolve_target_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat.id
    
    # 1. Reply edilibsə
    if message.reply_to_message:
        return message.reply_to_message.from_user, context.args
        
    # 2. Tag və ya @username yazılibsə
    if context.args:
        first_arg = context.args[0]
        if first_arg.startswith("@"):
            target_username = first_arg[1:].lower()
            
            # Entity içində text_mention varsa
            if message.entities:
                for entity in message.entities:
                    if entity.type == "text_mention":
                        return entity.user, context.args[1:]
            
            # Əgər birbaşa klaviaturadan yazıbsa, qrup üzvünün adını/ID-sini əldə etməyə çalışırıq
            # Telegram-da birbaşa username-ə görə user object almaq üçün adminlər və ya son mesaj yazanlar yoxlanılır.
            # Alternativ olaraq, əgər bot qrupdakı üzvü tapa bilməsə belə, Telegram API-nin get_chat_member metodu 
            # bəzi hallarda username dəstəkləmir, lakin biz bunu try-except ilə idarə edirik.
            try:
                # Qrupdakı administratorlar siyahısından axtaraq
                admins = await context.bot.get_chat_administrators(chat_id)
                for admin in admins:
                    if admin.user.username and admin.user.username.lower() == target_username:
                        return admin.user, context.args[1:]
            except Exception:
                pass
                
            # Əgər hələ də tapılmırsa, xüsusi obyekt yaradırıq ki, bot xəta verməsin
            class TempUser:
                def __init__(self, uname):
                    self.id = None
                    self.first_name = f"@{uname}"
                    self.username = uname
            
            return TempUser(target_username), context.args[1:]

    return None, context.args

# Xoş gəldin tənzimləmələri
async def welcome_settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    chat_id = update.effective_chat.id
    
    if chat_id not in group_settings:
        group_settings[chat_id] = {"welcome_status": True, "welcome_text": DEFAULT_WELCOME_TEXT}

    if not context.args:
        await update.message.reply_text(
            "⚙️ **Xoş Gəldin Sisteminin İdarə Edilməsi:**\n\n"
            "• `/welcome on` — Aktivləşdirmək\n"
            "• `/welcome off` — Bağlamaq\n"
            "• `/setwelcome [mətn]` — Mesajı dəyişmək", 
            parse_mode="Markdown"
        )
        return

    arg = context.args[0].lower()
    if arg == "on":
        group_settings[chat_id]["welcome_status"] = True
        await update.message.reply_text("✨ Xoş gəldin mesajı uğurla **aktivləşdirildi**.", parse_mode="Markdown")
    elif arg == "off":
        group_settings[chat_id]["welcome_status"] = False
        await update.message.reply_text("❌ Xoş gəldin mesajı **söndürüldü**.", parse_mode="Markdown")

async def set_welcome_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    chat_id = update.effective_chat.id
    
    if not context.args:
        await update.message.reply_text("⚠️ Zəhmət olmasa yeni mətni daxil edin.", parse_mode="Markdown")
        return
        
    new_text = " ".join(context.args)
    if chat_id not in group_settings:
        group_settings[chat_id] = {"welcome_status": True, "welcome_text": DEFAULT_WELCOME_TEXT}
        
    group_settings[chat_id]["welcome_text"] = new_text
    await update.message.reply_text("✅ Yeni xoş gəldin şablonu yadda saxlanıldı!", parse_mode="Markdown")

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result: return
    
    chat_id = result.chat.id
    if chat_id not in group_settings:
        group_settings[chat_id] = {"welcome_status": True, "welcome_text": DEFAULT_WELCOME_TEXT}
        
    if not group_settings[chat_id]["welcome_status"]: return

    old_member = result.old_chat_member
    new_member = result.new_chat_member
    
    if old_member.status in ["left", "banned"] and new_member.status == "member":
        user = new_member.user
        user_mention = f"[{user.first_name}](tg://user?id={user.id})"
        user_name = user.first_name
        user_username = f"@{user.username}" if user.username else "Yoxdur"
        user_id = user.id
        
        template = group_settings[chat_id]["welcome_text"]
        final_message = template.replace("{user_mention}", user_mention)\
                                .replace("{user_name}", user_name)\
                                .replace("{user_username}", user_username)\
                                .replace("{user_id}", str(user_id))
        
        try:
            await context.bot.send_message(chat_id=chat_id, text=final_message, parse_mode="Markdown")
        except Exception as e:
            print(f"Xoş gəldin xətası: {e}")

# MUTE KOMUTU
async def manual_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    message = update.message
    chat_id = message.chat.id

    target_user, remaining_args = await resolve_target_user(update, context)
    if not target_user:
        await message.reply_text("⚠️ Zəhmət olmasa istifadəçini **tag edin** (məsələn: `/mute @salamqaqa 10m`) və ya mesajına **reply** atın!", parse_mode="Markdown")
        return

    if getattr(target_user, 'id', None) is None:
        await message.reply_text(f"⚠️ `{target_user.first_name}` qrupda tapılmadı. Zəhmət olmasa həmin şəxsin mesajına **reply** ataraq mute edin.", parse_mode="Markdown")
        return

    target_mention = f"[{target_user.first_name}](tg://user?id={target_user.id})"

    try:
        target_member = await context.bot.get_chat_member(chat_id, target_user.id)
        if target_member.status in ['creator', 'administrator']:
            await message.reply_text("❌ **Əmr yerinə yetirilmədi:** Admini və ya qrup sahibini mute edə bilməzsən!", parse_mode="Markdown")
            return
    except Exception:
        pass

    time_arg = remaining_args[0] if remaining_args else None
    duration = parse_time(time_arg) if time_arg else 0
    mute_until = int(time.time() + duration) if duration > 0 else 0
    duration_text = time_arg if time_arg else "Sonsuz (Admin qaldırana qədər)"

    try:
        await context.bot.restrict_chat_member(
            chat_id, target_user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=mute_until
        )
        success_msg = (
            "╭━ 🔇 **İSTİFADƏÇİ SƏSSİZƏ ALINDI** 🔇 ━╮\n\n"
            f"👤 **İstifadəçi:** {target_mention}\n"
            f"⏱ **Müddət:** `{duration_text}`\n"
            "📜 **Status:** Mesaj yazmaq hüququ məhdudlaşdırıldı.\n\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
        )
        await message.reply_text(success_msg, parse_mode="Markdown")
    except Exception as e:
        await message.reply_text(f"❌ Xəta baş verdi: {e}")

# UNMUTE KOMUTU
async def manual_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    message = update.message
    chat_id = message.chat.id
    
    target_user, _ = await resolve_target_user(update, context)
    if not target_user or getattr(target_user, 'id', None) is None:
        await message.reply_text("⚠️ Zəhmət olmasa səssizliyini qaldırmaq istədiyiniz şəxsin **mesajına cavab verin** və ya tag edin!", parse_mode="Markdown")
        return

    target_mention = f"[{target_user.first_name}](tg://user?id={target_user.id})"

    try:
        member = await context.bot.get_chat_member(chat_id, target_user.id)
        if member.status == "member" and getattr(member, 'can_send_messages', True):
            await message.reply_text(f"ℹ️ **Bildiriş:** {target_mention} onsuz da mute-də deyil!", parse_mode="Markdown")
            return
    except Exception:
        pass

    try:
        await context.bot.restrict_chat_member(
            chat_id, target_user.id,
            permissions=ChatPermissions(
                can_send_messages=True, can_send_audios=True, can_send_documents=True,
                can_send_photos=True, can_send_videos=True, can_send_video_notes=True,
                can_send_voice_notes=True, can_send_polls=True, can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
        unmute_msg = (
            "╭━ 🔊 **SƏSSİZLİK QALDIRILDI** 🔊 ━╮\n\n"
            f"👤 **İstifadəçi:** {target_mention}\n"
            "📜 **Status:** Yenidən mesaj yazmaq hüququ verildi.\n\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
        )
        await message.reply_text(unmute_msg, parse_mode="Markdown")
    except Exception as e:
        await message.reply_text(f"❌ Xəta baş verdi: {e}")

# BAN KOMUTU
async def manual_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    message = update.message
    chat_id = message.chat.id
    
    target_user, _ = await resolve_target_user(update, context)
    if not target_user or getattr(target_user, 'id', None) is None:
        await message.reply_text("⚠️ Zəhmət olmasa banlamaq istədiyiniz şəxsin **mesajına cavab verin** və ya tag edin!", parse_mode="Markdown")
        return

    target_mention = f"[{target_user.first_name}](tg://user?id={target_user.id})"

    try:
        target_member = await context.bot.get_chat_member(chat_id, target_user.id)
        if target_member.status in ['creator', 'administrator']:
            await message.reply_text("❌ **Əmr yerinə yetirilmədi:** Admini və ya qrup sahibini ban edə bilməzsən!", parse_mode="Markdown")
            return
    except Exception:
        pass

    try:
        await context.bot.ban_chat_member(chat_id, target_user.id)
        ban_msg = (
            "╭━ 🔨 **İSTİFADƏÇİ BAN OLUNDU** 🔨 ━╮\n\n"
            f"👤 **İstifadəçi:** {target_mention}\n"
            "🗑 **Status:** Qrupdan qovuldu və geri gələ bilməz!\n\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
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
        member = await context.bot.get_chat_member(chat_id, user_id)
        if member.status != "kicked":
            await message.reply_text(f"ℹ️ **Bildiriş:** Bu ID-yə sahib (`{user_id}`) istifadəçi onsuz da ban olunmayıb!", parse_mode="Markdown")
            return

        await context.bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
        unban_msg = (
            "╭━ 🔓 **BAN QALDIRILDI** 🔓 ━╮\n\n"
            f"👤 **İstifadəçi ID:** `{user_id}`\n"
            "📜 **Status:** Ban qaldırıldı, yenidən qrupa qoşula bilər.\n\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
        )
        await message.reply_text(unban_msg, parse_mode="Markdown")
    except Exception as e:
        await message.reply_text(f"❌ Xəta baş verdi (ID-ni düzgün yazdığınızdan əmin olun): {e}")

# WARN KOMUTU
async def manual_warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    message = update.message
    chat_id = message.chat.id
    
    target_user, remaining_args = await resolve_target_user(update, context)
    if not target_user or getattr(target_user, 'id', None) is None:
        await message.reply_text("⚠️ Zəhmət olmasa xəbərdarlıq vermək istədiyiniz şəxsin **mesajına cavab verin** və ya tag edin!", parse_mode="Markdown")
        return

    target_mention = f"[{target_user.first_name}](tg://user?id={target_user.id})"
    
    try:
        target_member = await context.bot.get_chat_member(chat_id, target_user.id)
        if target_member.status in ['creator', 'administrator']:
            await message.reply_text("❌ **Əmr yerinə yetirilmədi:** Adminə xəbərdarlıq vermək olmaz!", parse_mode="Markdown")
            return
    except Exception:
        pass

    reason = " ".join(remaining_args) if remaining_args else "Göstərilməyib"
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
                "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
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
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
        )
        await message.reply_text(warn_msg, parse_mode="Markdown")

# UNWARN KOMUTU
async def manual_unwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    message = update.message
    chat_id = message.chat.id
    
    target_user, _ = await resolve_target_user(update, context)
    if not target_user or getattr(target_user, 'id', None) is None:
        await message.reply_text("⚠️ Zəhmət olmasa xəbərdarlığını silmək istədiyiniz şəxsin **mesajına cavab verin**!", parse_mode="Markdown")
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
            "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
        )
        await message.reply_text(unwarn_msg, parse_mode="Markdown")
    else:
        await message.reply_text("ℹ️ **Bildiriş:** Bu istifadəçinin aktiv xəbərdarlığı yoxdur.", parse_mode="Markdown")

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
                "╰━━━━━━━━━━━━━━━━━━━━━━╯"
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
                "╰━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
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
    app.add_handler(CommandHandler("welcome", welcome_settings_cmd))
    app.add_handler(CommandHandler("setwelcome", set_welcome_text))
    
    app.add_handler(ChatMemberHandler(welcome_new_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), anti_spam))
    
    print("Bot PRO v8.0 işə düşdü...")
    app.run_polling()

if __name__ == '__main__':
    main()
