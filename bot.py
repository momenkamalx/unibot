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

# نصيحة جيف: يفضل وضع التوكن في متغيرات البيئة في Railway
BOT_TOKEN = os.getenv("BOT_TOKEN", "8622262776:AAEkLsx5YGFV1JUNSV3HI07MRw7dzdbkoaU")
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

# ==================== BROWSE & FILES ====================
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
    if file["file_type"] == "video" and str(file["telegram_file_id"]).startswith("http"):
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
        "sheet": "أرسل الملف الآن (PDF, Word...)\nقبل الإرسال، اكتب عنوان الملف في رسالة.",
        "video": "أرسل الفيديو مباشرة.\nقبل الإرسال، اكتب عنوان الفيديو في رسالة.",
        "link": "أرسل الرابط.\nقبل الإرسال، اكتب عنوان الرابط في رسالة.",
        "summary": "أرسل الملخص.\nقبل الإرسال، اكتب عنوان الملخص في رسالة.",
    }
    context.user_data["waiting_title"] = True
    await query.edit_message_text(f"📝 {messages[upload_type]}")

async def handle_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["upload_title"] = update.message.text
    context.user_data["waiting_title"] = False
    await update.message.reply_text("✅ العنوان تم. الآن أرسل الملف أو الرابط.")

async def handle_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_upload"): return
    user, subject_id, upload_type = update.effective_user, context.user_data.get("upload_subject"), context.user_data.get("upload_type")
    title = context.user_data.get("upload_title", "بدون عنوان")
    
    file_id, c_type = "", "document"
    if update.message.document: file_id, c_type = update.message.document.file_id, "document"
    elif update.message.video: file_id, c_type = update.message.video.file_id, "video"
    elif update.message.photo: file_id, c_type = update.message.photo[-1].file_id, "photo"
    elif update.message.text and update.message.text.startswith("http"): file_id, c_type = update.message.text, "link"
    else: return

    pending_id = db.add_pending(subject_id, upload_type, title, file_id, c_type, user.id, user.full_name)
    context.user_data["waiting_upload"] = False
    await update.message.reply_text("✅ تم إرسال الملف للمراجعة!")
    
    for admin_id in ADMIN_IDS:
        try:
            kb = [[InlineKeyboardButton("✅ موافقة", callback_data=f"approve_{pending_id}"), InlineKeyboardButton("❌ رفض", callback_data=f"reject_{pending_id}")]]
            await context.bot.send_message(admin_id, f"📬 طلب رفع جديد!\n👤 {user.full_name}\n📝 {title}", reply_markup=InlineKeyboardMarkup(kb))
        except: pass

# ==================== ADMIN ACTIONS (جديد) ====================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ADMIN_IDS: return
    pending_count = db.count_pending()
    keyboard = [
        [InlineKeyboardButton(f"📬 طلبات الرفع ({pending_count})", callback_data="admin_pending")],
        [InlineKeyboardButton("➕ إضافة مادة", callback_data="admin_add_subject")],
        [InlineKeyboardButton("📂 إدارة الملفات (حذف/تعديل)", callback_data="admin_manage_subs")],
        [InlineKeyboardButton("👥 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_home")],
    ]
    await query.edit_message_text("⚙️ لوحة الأدمن:", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_manage_subs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subjects = db.get_subjects()
    keyboard = [[InlineKeyboardButton(f"📁 {s['name']}", callback_data=f"managesub_{s['id']}")] for s in subjects]
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")])
    await query.edit_message_text("اختر المادة لإدارة ملفاتها:", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject_id = query.data.split("_")[1]
    files = db.get_all_files_by_subject(subject_id) 
    if not files:
        await query.edit_message_text("لا توجد ملفات.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="admin_manage_subs")]]))
        return
    await query.edit_message_text("إليك الملفات (سيتم إرسالها كرسائل منفصلة):")
    for f in files:
        kb = [[InlineKeyboardButton("🗑️ حذف", callback_data=f"confdel_{f['id']}"), InlineKeyboardButton("✏️ تعديل الاسم", callback_data=f"editname_{f['id']}")]]
        await query.message.reply_text(f"📄 {f['title']}\nالنوع: {f['file_type']}", reply_markup=InlineKeyboardMarkup(kb))

async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    file_id = query.data.split("_")[1]
    db.delete_file(file_id)
    await query.edit_message_text("🗑️ تم حذف الملف نهائياً.")

async def request_edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["editing_file_id"] = query.data.split("_")[1]
    context.user_data["waiting_new_name"] = True
    await query.message.reply_text("أرسل الاسم الجديد للملف الآن:")

async def handle_new_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = context.user_data.get("editing_file_id")
    new_name = update.message.text.strip()
    db.update_file_title(file_id, new_name)
    context.user_data["waiting_new_name"] = False
    await update.message.reply_text(f"✅ تم تغيير الاسم إلى: {new_name}")

# ==================== REST OF ADMIN ====================
async def approve_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pending_id = query.data.split("_")[1]
    db.approve_pending(pending_id)
    await query.edit_message_text(f"✅ تم القبول ونشر الملف.")

async def reject_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db.reject_pending(query.data.split("_")[1])
    await query.edit_message_text("❌ تم رفض الطلب.")

async def admin_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pendings = db.get_pending()
    if not pendings:
        await query.edit_message_text("لا توجد طلبات معلقة.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="admin_panel")]]))
        return
    for p in pendings:
        kb = [[InlineKeyboardButton("✅ موافقة", callback_data=f"approve_{p['id']}"), InlineKeyboardButton("❌ رفض", callback_data=f"reject_{p['id']}")]]
        await query.message.reply_text(f"📬 طلب #{p['id']}\n👤 {p['uploader_name']}\n📝 {p['title']}", reply_markup=InlineKeyboardMarkup(kb))

async def admin_add_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["waiting_subject_name"] = True
    await query.edit_message_text("اكتب اسم المادة الجديدة:")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(f"📊 الإحصائيات:\nالمستخدمون: {db.count_users()}\nالملفات: {db.count_files()}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data="admin_panel")]]))

async def handle_subject_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    context.user_data["waiting_search"] = False
    results = db.search_files(update.message.text.strip())
    if not results:
        await update.message.reply_text("لم يتم العثور على نتائج.")
        return
    kb = [[InlineKeyboardButton(f"⬇️ {r['title']}", callback_data=f"getfile_{r['id']}")] for r in results]
    await update.message.reply_text("نتائج البحث:", reply_markup=InlineKeyboardMarkup(kb))

async def back_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("📚 تصفح المواد", callback_data="browse")], [InlineKeyboardButton("⬆️ رفع ملف", callback_data="upload_info")], [InlineKeyboardButton("🔍 بحث", callback_data="search_prompt")]]
    if query.from_user.id in ADMIN_IDS: keyboard.append([InlineKeyboardButton("⚙️ لوحة الأدمن", callback_data="admin_panel")])
    await query.edit_message_text("القائمة الرئيسية:", reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== ROUTER & MAIN ====================
async def handle_text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("waiting_title"): await handle_title(update, context)
    elif context.user_data.get("waiting_subject_name"): await handle_subject_name(update, context)
    elif context.user_data.get("waiting_search"): await handle_search(update, context)
    elif context.user_data.get("waiting_new_name"): await handle_new_name(update, context)
    elif context.user_data.get("waiting_upload") and update.message.text.startswith("http"): await handle_upload(update, context)

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
    app.add_handler(CallbackQueryHandler(admin_manage_subs, pattern="^admin_manage_subs$"))
    app.add_handler(CallbackQueryHandler(admin_list_files, pattern="^managesub_"))
    app.add_handler(CallbackQueryHandler(confirm_delete, pattern="^confdel_"))
    app.add_handler(CallbackQueryHandler(request_edit_name, pattern="^editname_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_router))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO | filters.PHOTO, handle_upload))
    app.run_polling()

if __name__ == "__main__": main()
