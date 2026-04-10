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

# استخدم التوكن الخاص بك هنا أو من متغيرات البيئة
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
        f"أهلاً {user.first_name}! 👋\n\n"
        "اختر من القائمة أدناه:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==================== GET FILE (تم التعديل: الاسم أولاً) ====================
async def get_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    file_id_db = query.data.split("_")[1]
    file = db.get_file_by_id(file_id_db)
    
    if not file:
        await query.edit_message_text("الملف غير موجود.")
        return

    caption_text = f"📎 {file['title']}\n👤 رفعه: {file['uploader_name']}"

    if file["content_type"] == "link":
        await query.message.reply_text(f"{caption_text}\n🔗 الرابط:\n{file['telegram_file_id']}")
    
    elif file["content_type"] == "document":
        await query.message.reply_text(f"⏳ جاري إرسال الملف: {file['title']}...") 
        await query.message.reply_document(file["telegram_file_id"], caption=caption_text)
    
    elif file["content_type"] == "video":
        await query.message.reply_text(f"⏳ جاري إرسال الفيديو: {file['title']}...") 
        await query.message.reply_video(file["telegram_file_id"], caption=caption_text)
    
    elif file["content_type"] == "photo":
        await query.message.reply_photo(file["telegram_file_id"], caption=caption_text)

# ==================== ADMIN STATS (تطوير الإحصائيات) ====================
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    count = db.count_users()
    files_count = db.count_files()
    users = db.get_all_users() # جلب قائمة المستخدمين
    
    stats_text = (
        f"📊 **إحصائيات البوت:**\n\n"
        f"👥 عدد المشتركين: {count}\n"
        f"📁 إجمالي الملفات: {files_count}\n\n"
        f"📋 **قائمة المستخدمين:**\n"
    )
    
    for u in users:
        username = f"@{u['username']}" if u['username'] else "بدون يوزر"
        stats_text += f"🔹 {u['name']} | ID: `{u['id']}` | {username}\n"

    # إذا كان النص طويلاً جداً سيتم إرساله كرسالة نصية
    if len(stats_text) > 4000:
        stats_text = stats_text[:3900] + "\n... (القائمة طويلة جداً)"

    await query.edit_message_text(
        stats_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]])
    )

# ==================== باقي الدوال الأساسية ====================

async def browse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subjects = db.get_subjects()
    if not subjects:
        await query.edit_message_text("لا توجد مواد بعد.")
        return
    keyboard = [[InlineKeyboardButton(f"📖 {s['name']}", callback_data=f"subject_{s['id']}")] for s in subjects]
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_home")])
    await query.edit_message_text("اختر المادة:", reply_markup=InlineKeyboardMarkup(keyboard))

async def subject_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject_id = query.data.split("_")[1]
    subject = db.get_subject(subject_id)
    keyboard = [
        [InlineKeyboardButton("📄 شيتات", callback_data=f"files_{subject_id}_sheet")],
        [InlineKeyboardButton("🎬 فيديوهات", callback_data=f"files_{subject_id}_video")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="browse")],
    ]
    await query.edit_message_text(f"📖 {subject['name']}:", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, subject_id, f_type = query.data.split("_")
    files = db.get_files(subject_id, f_type)
    if not files:
        await query.edit_message_text("لا توجد ملفات.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙", callback_data=f"subject_{subject_id}")]]))
        return
    keyboard = [[InlineKeyboardButton(f"⬇️ {f['title']}", callback_data=f"getfile_{f['id']}")] for f in files]
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data=f"subject_{subject_id}")])
    await query.edit_message_text("اختر الملف:", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kb = [
        [InlineKeyboardButton(f"📬 طلبات معلقة ({db.count_pending()})", callback_data="admin_pending")],
        [InlineKeyboardButton("📊 الإحصائيات والمستخدمين", callback_data="admin_stats")],
        [InlineKeyboardButton("📂 إدارة الملفات", callback_data="admin_manage_subs")],
        [InlineKeyboardButton("➕ إضافة مادة", callback_data="admin_add_subject")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_home")],
    ]
    await query.edit_message_text("⚙️ لوحة التحكم:", reply_markup=InlineKeyboardMarkup(kb))

async def back_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [[InlineKeyboardButton("📚 تصفح المواد", callback_data="browse")], [InlineKeyboardButton("⬆️ رفع ملف", callback_data="upload_info")], [InlineKeyboardButton("🔍 بحث", callback_data="search_prompt")]]
    if query.from_user.id in ADMIN_IDS: keyboard.append([InlineKeyboardButton("⚙️ لوحة الأدمن", callback_data="admin_panel")])
    await query.edit_message_text("القائمة الرئيسية:", reply_markup=InlineKeyboardMarkup(keyboard))

# (ملاحظة: الدوال الأخرى مثل handle_upload و admin_pending تبقى كما هي في الكود السابق)
# سأختصر الكود هنا لسهولة النسخ، تأكد من وجود الـ Handlers في دالة main

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Handlers الأساسية
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(browse, pattern="^browse$"))
    app.add_handler(CallbackQueryHandler(subject_menu, pattern="^subject_"))
    app.add_handler(CallbackQueryHandler(show_files, pattern="^files_"))
    app.add_handler(CallbackQueryHandler(get_file, pattern="^getfile_"))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(admin_stats, pattern="^admin_stats$"))
    app.add_handler(CallbackQueryHandler(back_home, pattern="^back_home$"))
    
    # تأكد من إضافة باقي الـ Handlers للحذف والتعديل والرفع هنا كما في الكود السابق
    
    print("✅ البوت شغال!")
    app.run_polling()

if __name__ == "__main__":
    main()
