
#!/usr/bin/env python3
"""
𝙼𝙴𝚁𝙾 𝙷𝙾𝚂𝚃 - بوت التحكم والاستضافة الخارقة المتكامل
طُوِّر بواسطة: 𝗘𝗛𝗔𝗕𝗔𝗜𝗛𝗔𝗪𝗕𝗔𝗡𝗜 | @Y_20_20
"""

import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ========== إعدادات البوت والاتصال ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN", "9090360556:AAFoWLDI0JrahWjI18bqeK0IILwpD58LIH8")
API_BASE_URL = os.environ.get("API_BASE_URL", "https://m33ero-host.onrender.com")

# إيدي الأدمن على تيليجرام
ADMIN_TELEGRAM_IDS = [1002670694]

# معلومات المطور
DEVELOPER_INFO = "🛠 طُوِّر بواسطة: *𝗘𝗛𝗔𝗕𝗔𝗜𝗛𝗔𝗪𝗕𝗔𝗡𝗜*\n📬 تواصل: @Y_20_20"

# ========== حالات المحادثة المتعددة ==========
(
    WAITING_FOR_API_KEY,
    WAITING_FOR_NEW_SERVER_NAME,
    WAITING_FOR_SERVER_TYPE,
    WAITING_FOR_DELETE_USERNAME,
) = range(4)


# ─────────────────────────────────────────────────
#  دالة التواصل الموحدة مع الـ Backend (API Helper)
# ─────────────────────────────────────────────────
def api_request(endpoint, method="GET", data=None, params=None, api_key=None):
    url = f"{API_BASE_URL}{endpoint}"
    try:
        if method == "GET":
            p = dict(params or {})
            if api_key:
                p["api_key"] = api_key
            resp = requests.get(url, params=p, timeout=30)
        else:
            d = dict(data or {})
            if api_key and "api_key" not in d:
                d["api_key"] = api_key
            resp = requests.post(url, json=d, timeout=30)
        return resp.json() if resp.ok else {"success": False, "message": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"success": False, "message": str(e)}


def is_admin_tg(update: Update) -> bool:
    user_id = update.effective_chat.id if update.effective_chat else update.effective_user.id
    return user_id in ADMIN_TELEGRAM_IDS


# ─────────────────────────────────────────────────
#  القائمة الرئيسية المحدثة
# ─────────────────────────────────────────────────
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    api_key = context.user_data.get("api_key")
    username = context.user_data.get("username", "")
    is_adm = is_admin_tg(update)

    keyboard = []

    if api_key:
        keyboard.append([
            InlineKeyboardButton("📁 ملفاتي وسيرفراتي", callback_data="my_servers"),
            InlineKeyboardButton("➕ رفع / إنشاء سيرفر", callback_data="create_server"),
        ])
        keyboard.append([
            InlineKeyboardButton("🔑 تغيير API Key", callback_data="change_api"),
            InlineKeyboardButton("🚪 تسجيل خروج", callback_data="logout"),
        ])
    else:
        keyboard.append([InlineKeyboardButton("🔑 ربط API Key", callback_data="enter_api")])

    if is_adm:
        pending_count = 0
        result = api_request("/api/admin/pending", api_key=api_key)
        if result and result.get("success"):
            pending_count = len(result.get("requests", []))
        bell = f"🔔 إشعارات الحسابات ({pending_count})" if pending_count > 0 else "🔕 لا إشعارات"
        keyboard.append([
            InlineKeyboardButton("👑 لوحة الإدارة الخارقة", callback_data="admin_panel"),
            InlineKeyboardButton(bell, callback_data="admin_notifications"),
        ])

    keyboard.append([InlineKeyboardButton("💬 تواصل مع المطور @Y_20_20", url="https://t.me/Y_20_20")])

    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "      𝙼𝙴𝚁𝙾 𝙷𝙾𝚂𝚃 🚀\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
    )
    if username:
        text += f"👤 أهلاً بك، *{username}*!\n"
    text += "✅ متصل بسيرفر المنصة بنجاح\n" if api_key else "⚠️ يرجى ربط الـ API Key أولاً للبدء\n"
    text += f"\n{DEVELOPER_INFO}"

    markup = InlineKeyboardMarkup(keyboard)
    try:
        if edit and update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=markup)
        elif update.message:
            await update.message.reply_text(text, parse_mode="Markdown", reply_markup=markup)
        else:
            await update.callback_query.message.edit_text(text, parse_mode="Markdown", reply_markup=markup)
    except Exception:
        pass


# ─────────────────────────────────────────────────
#  عرض السيرفرات والملفات (دعم HTML, JS, PHP, PY)
# ─────────────────────────────────────────────────
async def show_servers_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    api_key = context.user_data.get("api_key")
    if not api_key:
        await query.edit_message_text("❌ يجب ربط API Key أولاً.")
        return

    result = api_request("/api/bot/servers", api_key=api_key)
    if not result or not result.get("success"):
        await query.edit_message_text(
            "━━━━━━━━━━━━━━━━━━━━\n"
            "❌ فشل جلب السيرفرات والملفات\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "تحقق من صحة الـ API Key أو حالة الاتصال.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")]]),
        )
        return

    servers = result.get("servers", [])
    if not servers:
        await query.edit_message_text(
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📭 لا توجد ملفات أو سيرفرات مرفوعة\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "قم برفع ملفك الأول عبر الموقع أو الزر أدناه!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ رفع ملف / إنشاء سيرفر", callback_data="create_server")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")],
            ]),
        )
        return

    await query.edit_message_text(f"📋 لديك *{len(servers)}* عناصر مستضافة:", parse_mode="Markdown")

    for srv in servers:
        status_emoji = "🟢" if srv.get("status", "Running") == "Running" else "⚫"
        srv_type = srv.get("type", "html").upper()
        
        # تحديد الأيقونة حسب نوع الملف المدعوم
        type_icon = "🌐"
        if srv_type == "JS": type_icon = "🟨"
        elif srv_type == "PHP": type_icon = "🐘"
        elif srv_type == "PY": type_icon = "🐍"

        text = (
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{status_emoji} *{srv.get('name', srv.get('title', 'ملف'))}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"{type_icon} نوع البيئة: `{srv_type}`\n"
            f"📊 الحالة: `{srv.get('status', 'نشط')}`\n"
            f"🔌 المنفذ/الرابط: `{srv.get('port', 'متصل')}`"
        )
        folder = srv.get("id", srv.get("folder", ""))
        keyboard = [
            [
                InlineKeyboardButton("▶️ تشغيل", callback_data=f"srv_start|{folder}"),
                InlineKeyboardButton("⏹ إيقاف", callback_data=f"srv_stop|{folder}"),
                InlineKeyboardButton("🔄 إعادة تشغيل", callback_data=f"srv_restart|{folder}"),
            ],
            [
                InlineKeyboardButton("🖥 كونسول السيرفر", callback_data=f"console|{folder}"),
                InlineKeyboardButton("⚠️ الأخطاء", callback_data=f"errors|{folder}"),
                InlineKeyboardButton("🗑 حذف", callback_data=f"srv_delete|{folder}"),
            ],
            [InlineKeyboardButton("📦 تثبيت الحزم والمكتبات", callback_data=f"install|{folder}")],
        ]
        await query.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    await query.message.reply_text(
        "━━━━━━━━━━━━━━━━━━━━",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]]),
    )


# ─────────────────────────────────────────────────
#  لوحة الإدارة الشاملة
# ─────────────────────────────────────────────────
async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin_tg(update):
        await query.edit_message_text("❌ غير مصرح لك بالدخول إلى لوحة الإدارة.")
        return

    api_key = context.user_data.get("api_key")
    result = api_request("/api/admin/users", api_key=api_key)
    users = result.get("users", []) if result and result.get("success") else []

    pending_result = api_request("/api/admin/pending", api_key=api_key)
    pending_count = len(pending_result.get("requests", [])) if pending_result and pending_result.get("success") else 0

    text = (
        "━━━━━━━━━━━━━━━━━━━━\n"
        "  👑 لوحة إدارة 𝙼𝙴𝚁𝙾 𝙷𝙾𝚂𝚃\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 إجمالي المستخدمين: *{len(users)}*\n"
        f"🔔 طلبات الحسابات المعلقة: *{pending_count}*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
    )
    for u in users[:10]:
        text += f"• `{u.get('username')}` | الخطة النشطة مفعلة\n"
    if len(users) > 10:
        text += f"... و {len(users) - 10} مستخدمين آخرين\n"

    bell = f"🔔 الطلبات ({pending_count})" if pending_count > 0 else "🔕 لا طلبات"
    keyboard = [
        [
            InlineKeyboardButton(bell, callback_data="admin_notifications"),
            InlineKeyboardButton("📊 إحصائيات النظام", callback_data="admin_stats"),
        ],
        [InlineKeyboardButton("🗑 حذف مستخدم من المنصة", callback_data="admin_delete_user")],
        [InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="main_menu")],
    ]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


# ─────────────────────────────────────────────────
#  إشعارات وموافقات الحسابات المعلقة للأدمن
# ─────────────────────────────────────────────────
async def show_admin_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin_tg(update):
        await query.edit_message_text("❌ غير مصرح.")
        return

    api_key = context.user_data.get("api_key")
    result = api_request("/api/admin/pending", api_key=api_key)

    if not result or not result.get("success"):
        await query.edit_message_text("❌ فشل جلب الإشعارات من السيرفر.")
        return

    requests_list = result.get("requests", [])

    if not requests_list:
        await query.edit_message_text(
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🔕 لا توجد طلبات حسابات معلقة\n"
            "━━━━━━━━━━━━━━━━━━━━",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]]),
        )
        return

    await query.edit_message_text(
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔔 طلبات الحسابات الجديدة ({len(requests_list)})\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    for req in requests_list:
        text = (
            f"👤 اسم المستخدم: `{req.get('username')}`\n"
            f"📅 التاريخ: {req.get('created_at', '')[:19]}"
        )
        keyboard = [[
            InlineKeyboardButton("✅ قبول الحساب", callback_data=f"approve|{req.get('username')}"),
            InlineKeyboardButton("❌ رفض الحساب", callback_data=f"reject|{req.get('username')}"),
        ]]
        await query.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    await query.message.reply_text(
        "━━━━━━━━━━━━━━━━━━━━",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]]),
    )


# ─────────────────────────────────────────────────
#  بدء التشغيل والأوامر (`/start`)
# ─────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    api_key = context.user_data.get("api_key")
    if api_key:
        result = api_request("/api/bot/verify", method="POST", data={"api_key": api_key})
        if result and result.get("success"):
            context.user_data["username"] = result.get("username")
            await show_main_menu(update, context)
            return ConversationHandler.END
        context.user_data.clear()

    keyboard = [
        [InlineKeyboardButton("🔑 إدخال API Key للربط", callback_data="enter_api")],
        [InlineKeyboardButton("💬 تواصل مع المطور @Y_20_20", url="https://t.me/Y_20_20")],
    ]
    await update.message.reply_text(
        "━━━━━━━━━━━━━━━━━━━━\n"
        "      𝙼𝙴𝚁𝙾 𝙷𝙾𝚂𝚃 🚀\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "منصة استضافة الملفات الشاملة (HTML, JS, PHP, Python)\n\n"
        "للحصول على حساب مفعل:\n"
        "📬 تواصل مع المطور: @Y_20_20\n\n"
        f"{DEVELOPER_INFO}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return WAITING_FOR_API_KEY


async def handle_api_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    api_key = update.message.text.strip()
    result = api_request("/api/bot/verify", method="POST", data={"api_key": api_key})
    if not result or not result.get("success"):
        keyboard = [[InlineKeyboardButton("💬 تواصل مع المطور", url="https://t.me/Y_20_20")]]
        await update.message.reply_text(
            "❌ *مفتاح API غير صالح أو خاطئ!*\n\n"
            "تأكد من نسخه بدقة من لوحة التحكم أو تواصل مع المطور: @Y_20_20",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return WAITING_FOR_API_KEY

    context.user_data["api_key"] = api_key
    context.user_data["username"] = result.get("username")
    context.user_data["is_admin"] = result.get("is_admin", False)

    await update.message.reply_text(
        f"✅ *تم ربط الحساب بنجاح!*\n"
        f"👤 أهلاً بك يا *{result.get('username')}*!",
        parse_mode="Markdown",
    )
    await show_main_menu(update, context)
    return ConversationHandler.END


# ─────────────────────────────────────────────────
#  إنشاء سيرفر جديد أو اختيار البيئة (.html, .js, .php, .py)
# ─────────────────────────────────────────────────
async def receive_server_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    context.user_data["pending_server_name"] = name
    
    # خيارات أنواع البيئات المدعومة بالكامل
    keyboard = [
        [
            InlineKeyboardButton("🌐 HTML / HTM", callback_data="server_type_html"),
            InlineKeyboardButton("🟨 JavaScript", callback_data="server_type_js"),
        ],
        [
            InlineKeyboardButton("🐘 PHP Server", callback_data="server_type_php"),
            InlineKeyboardButton("🐍 Python / Bot", callback_data="server_type_python"),
        ]
    ]
    await update.message.reply_text(
        f"📦 *اختر نوع بيئة التشغيل المستهدفة:*\n\nاسم الملف/السيرفر: `{name}`",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return WAITING_FOR_SERVER_TYPE


async def receive_server_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    type_mapping = {
        "server_type_html": "HTML",
        "server_type_js": "Node.js/JS",
        "server_type_php": "PHP",
        "server_type_python": "Python"
    }
    
    srv_type = type_mapping.get(query.data, "Python")
    name = context.user_data.get("pending_server_name", "Project")

    result = api_request("/api/bot/create_server", method="POST", data={
        "api_key": context.user_data["api_key"],
        "name": name,
        "server_type": srv_type,
        "plan": "free",
        "storage": 500,
        "ram": 512,
        "cpu": 1.0,
    })

    if result and result.get("success"):
        await query.edit_message_text(
            f"✅ *تم تجهيز السيرفر والبيئة بنجاح!*\n\n"
            f"📛 الاسم: `{name}`\n"
            f"⚙️ النوع: `{srv_type}`\n\n"
            f"يمكنك رفع ملفك المخصص مباشرة عبر موقع المنصة.",
            parse_mode="Markdown",
        )
    else:
        await query.edit_message_text(
            f"❌ *فشل إعداد السيرفر!*\n{result.get('message', 'خطأ غير معروف في السيرفر')}",
            parse_mode="Markdown",
        )

    await show_main_menu(update, context)
    return ConversationHandler.END


# ─────────────────────────────────────────────────
#  الكونسول وسجل الأخطاء
# ─────────────────────────────────────────────────
async def show_console(update: Update, context: ContextTypes.DEFAULT_TYPE, folder: str):
    query = update.callback_query
    result = api_request("/api/bot/console", params={"folder": folder}, api_key=context.user_data.get("api_key"))
    if result and result.get("success"):
        logs = result.get("logs", "لا توجد سجلات تشغيل حالية")
        if len(logs) > 3500:
            logs = "...\n" + logs[-3500:]
        keyboard = [[
            InlineKeyboardButton("🔄 تحديث السجلات", callback_data=f"console|{folder}"),
            InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="my_servers"),
        ]]
        await query.edit_message_text(
            f"🖥 *كونسول السيرفر والبيئة*\n```\n{logs}\n```",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:
        await query.edit_message_text("❌ فشل جلب مخرجات الكونسول.")


async def show_errors(update: Update, context: ContextTypes.DEFAULT_TYPE, folder: str):
    query = update.callback_query
    result = api_request("/api/bot/errors", params={"folder": folder}, api_key=context.user_data.get("api_key"))
    if result and result.get("success"):
        errors = result.get("errors", "✅ ممتاز: لا توجد أي أخطاء مسجلة")
        if len(errors) > 3500:
            errors = "...\n" + errors[-3500:]
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="my_servers")]]
        await query.edit_message_text(
            f"⚠️ *سجل الأخطاء والتنبيهات*\n```\n{errors}\n```",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:
        await query.edit_message_text("❌ فشل جلب سجل الأخطاء.")


# ─────────────────────────────────────────────────
#  إدارة حذف المستخدمين والإحصائيات (أدمن)
# ─────────────────────────────────────────────────
async def admin_delete_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin_tg(update):
        await query.edit_message_text("❌ غير مصرح لك بذلك.")
        return ConversationHandler.END
    await query.edit_message_text("📝 أرسل الآن اسم المستخدم (Username) المراد حذفه نهائياً من المنصة:")
    return WAITING_FOR_DELETE_USERNAME


async def admin_delete_user_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip()
    result = api_request("/api/admin/delete-user", method="POST", data={
        "api_key": context.user_data.get("api_key"),
        "username": username,
    })
    if result and result.get("success"):
        await update.message.reply_text(f"✅ تم حذف المستخدم `{username}` وجميع ملفاته بنجاح", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ فشل الحذف: {result.get('message', 'خطأ غير متوقع')}")
    await show_main_menu(update, context)
    return ConversationHandler.END


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    metrics = api_request("/api/system/metrics")
    cpu = metrics.get("cpu", "0") if metrics else "0"
    ram = metrics.get("memory", "0") if metrics else "0"
    disk = metrics.get("disk", "0") if metrics else "0"
    await query.edit_message_text(
        "━━━━━━━━━━━━━━━━━━━━\n"
        "  📊 إحصائيات استهلاك النظام\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🖥 استهلاك المعالج CPU:  *{cpu}%*\n"
        f"💾 استهلاك الذاكرة RAM:  *{ram}%*\n"
        f"💿 المساحة المستخدمة Disk: *{disk}%*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]]),
    )


# ─────────────────────────────────────────────────
#  المعالج الرئيسي للأزرار التفاعلية (Callback Query Handler)
# ─────────────────────────────────────────────────
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "main_menu":
        await show_main_menu(update, context, edit=True)
    elif data == "my_servers":
        await show_servers_list(update, context)
    elif data in ("enter_api", "change_api"):
        context.user_data.pop("api_key", None)
        await query.edit_message_text(
            "🔑 *أدخل مفتاح الـ API الخاص بك أدناه:*\n\n"
            "يمكنك استخراجه مباشرة من لوحة حسابك في الموقع.",
            parse_mode="Markdown",
        )
        return WAITING_FOR_API_KEY
    elif data == "logout":
        context.user_data.clear()
        await query.edit_message_text("🚪 تم تسجيل الخروج من جلستك بنجاح.\nاستخدم الأمر /start لإعادة الدخول.")
    elif data == "create_server":
        await query.edit_message_text(
            "➕ *إنشاء سيرفر جديد أو رفع ملف استضافة*\n\n📝 أرسل اسم السيرفر أو الملف:",
            parse_mode="Markdown",
        )
        return WAITING_FOR_NEW_SERVER_NAME
    elif data == "admin_panel":
        await show_admin_panel(update, context)
    elif data == "admin_notifications":
        await show_admin_notifications(update, context)
    elif data == "admin_delete_user":
        return await admin_delete_user_start(update, context)
    elif data == "admin_stats":
        await admin_stats(update, context)

    # معالجة الأوامر التي تحتوي على فاصل الإجراءات "|"
    elif "|" in data:
        cmd, value = data.split("|", 1)
        api_key = context.user_data.get("api_key")

        if cmd in ("srv_start", "srv_stop", "srv_restart", "srv_delete"):
            action = cmd.replace("srv_", "")
            result = api_request("/api/bot/server/action", method="POST", data={
                "api_key": api_key, "folder": value, "action": action,
            })
            if result and result.get("success"):
                await query.answer(result.get("message", "✅ تمت العملية بنجاح")[:200], show_alert=True)
            else:
                await query.answer(f"❌ {result.get('message', 'فشل التنفيذ') if result else 'خطأ'}"[:200], show_alert=True)
            await show_servers_list(update, context)

        elif cmd == "console":
            await show_console(update, context, value)

        elif cmd == "errors":
            await show_errors(update, context, value)

        elif cmd == "install":
            result = api_request("/api/bot/install", method="POST", data={
                "api_key": api_key, "folder": value,
            })
            msg = result.get("message", "✅ جاري تثبيت الحزم المطلوبة") if result and result.get("success") else f"❌ {result.get('message','فشل التثبيت') if result else 'خطأ'}"
            await query.edit_message_text(
                f"📦 *إدارة الحزم والمكتبات*\n\n{msg}\n\nتابع الكونسول للوقوف على التحديثات.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🖥 فتح الكونسول", callback_data=f"console|{value}"),
                    InlineKeyboardButton("🔙 رجوع", callback_data="my_servers"),
                ]]),
            )

        elif cmd == "approve":
            result = api_request("/api/admin/approve", method="POST", data={
                "api_key": api_key, "username": value,
            })
            msg = f"✅ تم قبول حساب المستخدم {value}" if result and result.get("success") else "❌ فشل قبول الحساب"
            await query.answer(msg, show_alert=True)
            await show_admin_notifications(update, context)

        elif cmd == "reject":
            result = api_request("/api/admin/reject", method="POST", data={
                "api_key": api_key, "username": value,
            })
            msg = f"🚫 تم رفض طلب الحساب {value}" if result and result.get("success") else "❌ فشل الرفض"
            await query.answer(msg, show_alert=True)
            await show_admin_notifications(update, context)

    return ConversationHandler.END


# ─────────────────────────────────────────────────
#  دالة التشغيل الرئيسية والربط الآمن للمنصة
# ─────────────────────────────────────────────────
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(button_callback),
        ],
        states={
            WAITING_FOR_API_KEY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_api_key)
            ],
            WAITING_FOR_NEW_SERVER_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_server_name)
            ],
            WAITING_FOR_SERVER_TYPE: [
                CallbackQueryHandler(receive_server_type, pattern="^server_type_")
            ],
            WAITING_FOR_DELETE_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_delete_user_confirm)
            ],
        },
        fallbacks=[CommandHandler("start", start)],
        per_user=True,
        per_chat=True,
    )

    application.add_handler(conv)
    print("🚀 𝙼𝙴𝚁𝙾 𝙷𝙾𝚂𝚃 Bot يعمل بكفاءة تامة 24/7...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

