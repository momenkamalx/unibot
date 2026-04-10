import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from database import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8622262776:AAEkLsx5YGFV1JUNSV3HI07MRw7dzdbkoaU"
ADMIN_IDS = [1187216216]

# ==================== START ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.full_name, user.username or "")
    keyboard = [
        [InlineKeyboardButton("📚 تصفح المواد", callback_data="browse")],
        [InlineKeyboardButton("⬆️ رفع ملف أو فيديو", callback_data="upload_info")],
        [InlineKeyboardButton("🔍 بحث", callback_data="search_prompt")],
    ]
    if user.id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("⚙️ لوحة الأدمن", callback_data="admin_panel")])

    await update.message.reply_text(
        f"أهلاً {user.first_name}! صلى على نبينا وحبيبنا محمد 👋\n\n"
        "ادعو لينا نتوفق السمستر ده ونتفوق في الحياة🎓\n"
        "اختر من القائمة:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==================== BROWSE ====================
async def browse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subjects = db.get_subjects()
    if not subjects:
        await query.edit_message_text("لا توجد مواد بعد. كن أول من يرفع! 📤")
        return
    keyboard = [[InlineKeyboardButton(f"📖 {s['name']}", callback_data=f"subject_{s['id']}")] for s in subjects]
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_home")])
    await query.edit_message_text("اختر المادة:", reply_markup=InlineKeyboardMarkup(keyboard))

async def subject_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject_id = query.data.split("_")[1]
    context.user_data["current_subject"] = subject_id
    subject = db.get_subject(subject_id)
    keyboard = [
        [InlineKeyboardButton("📄 شيتات وملفات", callback_data=f"files_{subject_id}_sheet")],
        [InlineKeyboardButton("🎬 فيديوهات", callback_data=f"files_{subject_id}_video")],
        [InlineKeyboardButton("📝 ملخصات", callback_data=f"files_{subject_id}_summary")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="browse")],
    ]
    await query.edit_message_text(
        f"📖 {subject['name']}\nاختر نوع المحتوى:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, subject_id, file_type = query.data.split("_")
    files = db.get_files(subject_id, file_type)
    type_names = {"sheet": "شيتات وملفات 📄", "video": "فيديوهات 🎬", "summary": "ملخصات 📝"}
    if not files:
        await query.edit_message_text(
            f"لا يوجد {type_names[file_type]} لهذه المادة بعد.\n\nارفع أول ملف! 📤",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data=f"subject_{subject_id}")]])
        )
        return
    keyboard = [[InlineKeyboardButton(f"⬇️ {f['title']}", callback_data=f"getfile_{f['id']}")] for f in files]
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data=f"subject_{subject_id}")])
    await query.edit_message_text(
        f"{type_names[file_type]}:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def get_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    file_id_db = query.data.split("_")[1]
    file = db.get_file_by_id(file_id_db)
    if not file:
        await query.edit_message_text("الملف غير موجود.")
        return
    await query.message.reply_text(f"📎 {file['title']}\n👤 رفعه: {file['uploader_name']}")
    if file["file_type"] == "video" and file["telegram_file_id"].startswith("http"):
        await query.message.reply_text(f"🔗 رابط الفيديو:\n{file['telegram_file_id']}")
    elif file["content_type"] == "document":
        await query.message.reply_document(file["telegram_file_id"])
    elif file["content_type"] == "video":
        await query.message.reply_video(file["telegram_file_id"])
    elif file["content_type"] == "photo":
        await query.message.reply_photo(file["telegram_file_id"])

# ==================== UPLOAD ====================
async def upload_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subjects = db.get_subjects()
    if not subjects:
        await query.edit_message_text("لا توجد مواد. تواصل مع الأدمن لإضافة المواد أولاً.")
        return
    keyboard = [[InlineKeyboardButton(f"📖 {s['name']}", callback_data=f"uploadto_{s['id']}")] for s in subjects]
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_home")])
    await query.edit_message_text("اختر المادة التي تريد الرفع إليها:", reply_markup=InlineKeyboardMarkup(keyboard))

async def choose_upload_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject_id = query.data.split("_")[1]
    context.user_data["upload_subject"] = subject_id
    keyboard = [
        [InlineKeyboardButton("📄 شيت أو ملف", callback_data="uploadtype_sheet")],
        [InlineKeyboardButton("🎬 فيديو (رفع مباشر)", callback_data="uploadtype_video")],
        [InlineKeyboardButton("🔗 رابط يوتيوب/درايف", callback_data="uploadtype_link")],
        [InlineKeyboardButton("📝 ملخص", callback_data="uploadtype_summary")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="upload_info")],
    ]
    await query.edit_message_text("إيش نوع المحتوى؟", reply_markup=InlineKeyboardMarkup(keyboard))

async def set_upload_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    upload_type = query.data.split("_")[1]
    context.user_data["upload_type"] = upload_type
    context.user_data["waiting_upload"] = True
    messages = {
        "sheet": "أرسل الملف الآن (PDF, Word, Excel, صورة...)\n\nقبل الإرسال، اكتب عنوان الملف في رسالة منفصلة.",
        "video": "أرسل الفيديو مباشرة.\n\nقبل الإرسال، اكتب عنوان الفيديو في رسالة منفصلة.",
        "link": "أرسل الرابط (يوتيوب أو درايف).\n\nقبل الإرسال، اكتب عنوان الفيديو في رسالة منفصلة.",
        "summary": "أرسل ملف الملخص.\n\nقبل الإرسال، اكتب عنوان الملخص في رسالة منفصلة.",
    }
    context.user_data["waiting_title"] = True
    await query.edit_message_text(f"📝 {messages[upload_type]}")

async def handle_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("waiting_title"):
        context.user_data["upload_title"] = update.message.text
        context.user_data["waiting_title"] = False
        await update.message.reply_text("✅ العنوان تم. الآن أرسل الملف أو الرابط.")

async def handle_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_upload"):
        return
    user = update.effective_user
    subject_id = context.user_data.get("upload_subject")
    upload_type = context.user_data.get("upload_type")
    title = context.user_data.get("upload_title", "بدون عنوان")

    telegram_file_id = ""
    content_type = "document"

    if update.message.document:
        telegram_file_id = update.message.document.file_id
        content_type = "document"
    elif update.message.video:
        telegram_file_id = update.message.video.file_id
        content_type = "video"
    elif update.message.photo:
        telegram_file_id = update.message.photo[-1].file_id
        content_type = "photo"
    elif update.message.text and update.message.text.startswith("http"):
        telegram_file_id = update.message.text
        content_type = "link"
    else:
        await update.message.reply_text("❌ لم أتعرف على الملف. جرب مرة ثانية.")
        return

    pending_id = db.add_pending(
        subject_id=subject_id,
        file_type=upload_type,
        title=title,
        telegram_file_id=telegram_file_id,
        content_type=content_type,
        uploader_id=user.id,
        uploader_name=user.full_name
    )

    context.user_data["waiting_upload"] = False
    context.user_data["upload_title"] = ""

    await update.message.reply_text(
        "✅ تم إرسال الملف للمراجعة!\n"
        "سيتم نشره بعد موافقة الأدمن. شكراً 🙏"
    )

    # notify admins
    subject = db.get_subject(subject_id)
    for admin_id in ADMIN_IDS:
        try:
            keyboard = [
                [
                    InlineKeyboardButton("✅ موافقة", callback_data=f"approve_{pending_id}"),
                    InlineKeyboardButton("❌ رفض", callback_data=f"reject_{pending_id}")
                ]
            ]
            await context.bot.send_message(
                admin_id,
                f"📬 طلب رفع جديد!\n\n"
                f"👤 المستخدم: {user.full_name}\n"
                f"📖 المادة: {subject['name']}\n"
                f"📁 النوع: {upload_type}\n"
                f"📝 العنوان: {title}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")

# ==================== ADMIN ====================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ADMIN_IDS:
        await query.edit_message_text("⛔ غير مصرح.")
        return
    pending_count = db.count_pending()
    keyboard = [
        [InlineKeyboardButton(f"📬 طلبات الرفع ({pending_count})", callback_data="admin_pending")],
        [InlineKeyboardButton("➕ إضافة مادة", callback_data="admin_add_subject")],
        [InlineKeyboardButton("🗑️ حذف مادة", callback_data="admin_delete_subject")],
        [InlineKeyboardButton("👥 عدد المستخدمين", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_home")],
    ]
    await query.edit_message_text("⚙️ لوحة الأدمن:", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ADMIN_IDS:
        return
    pendings = db.get_pending()
    if not pendings:
        await query.edit_message_text(
            "لا توجد طلبات معلقة. ✅",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]])
        )
        return
    for p in pendings:
        keyboard = [[
            InlineKeyboardButton("✅ موافقة", callback_data=f"approve_{p['id']}"),
            InlineKeyboardButton("❌ رفض", callback_data=f"reject_{p['id']}")
        ]]
        subject = db.get_subject(p["subject_id"])
        await query.message.reply_text(
            f"📬 طلب #{p['id']}\n"
            f"👤 {p['uploader_name']}\n"
            f"📖 {subject['name']}\n"
            f"📁 {p['file_type']}\n"
            f"📝 {p['title']}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    await query.edit_message_text("الطلبات المعلقة 👆")

async def approve_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ADMIN_IDS:
        return
    pending_id = query.data.split("_")[1]
    db.approve_pending(pending_id)
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(f"✅ تم قبول الطلب #{pending_id} ونشره.")

async def reject_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ADMIN_IDS:
        return
    pending_id = query.data.split("_")[1]
    db.reject_pending(pending_id)
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(f"❌ تم رفض الطلب #{pending_id}.")

async def admin_add_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ADMIN_IDS:
        return
    context.user_data["waiting_subject_name"] = True
    await query.edit_message_text("اكتب اسم المادة الجديدة:")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    count = db.count_users()
    files_count = db.count_files()
    users = db.get_all_users()
    
    users_text = ""
    for u in users:
        username = f"@{u['username']}" if u['username'] else "بدون يوزر"
        users_text += f"👤 {u['name']} | {u['id']} | {username}\n"
    
    await query.edit_message_text(
        f"📊 الإحصائيات:\n\n"
        f"👥 المستخدمون: {count}\n"
        f"📁 الملفات المنشورة: {files_count}\n\n"
        f"قائمة المستخدمين:\n{users_text}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]])
    )

async def handle_subject_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("waiting_subject_name") and update.effective_user.id in ADMIN_IDS:
        name = update.message.text.strip()
        db.add_subject(name)
        context.user_data["waiting_subject_name"] = False
        await update.message.reply_text(f"✅ تمت إضافة مادة: {name}")

async def search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["waiting_search"] = True
    await query.edit_message_text("🔍 اكتب اسم الملف أو المادة للبحث:")

async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_search"):
        return
    context.user_data["waiting_search"] = False
    keyword = update.message.text.strip()
    results = db.search_files(keyword)
    if not results:
        await update.message.reply_text("لم يتم العثور على نتائج. 🔍")
        return
    keyboard = [[InlineKeyboardButton(f"⬇️ {r['title']}", callback_data=f"getfile_{r['id']}")] for r in results]
    await update.message.reply_text(
        f"نتائج البحث عن: {keyword}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def back_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    keyboard = [
        [InlineKeyboardButton("📚 تصفح المواد", callback_data="browse")],
        [InlineKeyboardButton("⬆️ رفع ملف أو فيديو", callback_data="upload_info")],
        [InlineKeyboardButton("🔍 بحث", callback_data="search_prompt")],
    ]
    if user.id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("⚙️ لوحة الأدمن", callback_data="admin_panel")])
    await query.edit_message_text("القائمة الرئيسية:", reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== MAIN ====================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(browse, pattern="^browse$"))
    app.add_handler(CallbackQueryHandler(subject_menu, pattern="^subject_"))
    app.add_handler(CallbackQueryHandler(show_files, pattern="^files_"))
    app.add_handler(CallbackQueryHandler(get_file, pattern="^getfile_"))
    app.add_handler(CallbackQueryHandler(upload_info, pattern="^upload_info$"))
    app.add_handler(CallbackQueryHandler(choose_upload_type, pattern="^uploadto_"))
    app.add_handler(CallbackQueryHandler(set_upload_type, pattern="^uploadtype_"))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(admin_pending, pattern="^admin_pending$"))
    app.add_handler(CallbackQueryHandler(approve_file, pattern="^approve_"))
    app.add_handler(CallbackQueryHandler(reject_file, pattern="^reject_"))
    app.add_handler(CallbackQueryHandler(admin_add_subject, pattern="^admin_add_subject$"))
    app.add_handler(CallbackQueryHandler(admin_stats, pattern="^admin_stats$"))
    app.add_handler(CallbackQueryHandler(search_prompt, pattern="^search_prompt$"))
    app.add_handler(CallbackQueryHandler(back_home, pattern="^back_home$"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_router))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO | filters.PHOTO, handle_upload))

    print("✅ البوت شغال!")
    app.run_polling()

async def handle_text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("waiting_title"):
        await handle_title(update, context)
    elif context.user_data.get("waiting_subject_name"):
        await handle_subject_name(update, context)
    elif context.user_data.get("waiting_search"):
        await handle_search(update, context)
    elif context.user_data.get("waiting_upload") and update.message.text.startswith("http"):
        await handle_upload(update, context)

if __name__ == "__main__":
    main()
