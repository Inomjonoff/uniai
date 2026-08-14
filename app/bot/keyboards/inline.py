"""
Inline Keyboards for Telegram Bot.
Includes Group Management, Recent Requests, and Unresolved Knowledge Learning Queue.
"""
from typing import List, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.db.models import TelegramGroup, UnresolvedQuery, TelegramMessage


def get_settings_keyboard(
    groups_count: int,
    knowledge_count: int,
    pending_learn_count: int = 0,
    auto_learning: bool = True,
    screenshot_analysis: bool = True
) -> InlineKeyboardMarkup:
    """Builds interactive main settings and management dashboard keyboard."""
    learn_icon = "🟢 ON" if auto_learning else "🔴 OFF"
    vision_icon = "🟢 ON" if screenshot_analysis else "🔴 OFF"

    keyboard = [
        [
            InlineKeyboardButton(text=f"Auto Learning: {learn_icon}", callback_data="toggle:auto_learning"),
            InlineKeyboardButton(text=f"Screenshot Vision: {vision_icon}", callback_data="toggle:screenshot_analysis")
        ],
        [
            InlineKeyboardButton(text=f"👥 Guruhlarni boshqarish ({groups_count})", callback_data="menu:groups"),
            InlineKeyboardButton(text=f"📨 Oxirgi murojaatlar", callback_data="menu:recent_messages")
        ],
        [
            InlineKeyboardButton(text=f"🎓 O'rganish kerak ({pending_learn_count})", callback_data="menu:unresolved_queue"),
            InlineKeyboardButton(text=f"📚 Bilimlar ({knowledge_count:,})", callback_data="menu:knowledge_stats")
        ],
        [
            InlineKeyboardButton(text="🔄 Yangilash", callback_data="menu:refresh_settings"),
            InlineKeyboardButton(text="✖️ Yopish", callback_data="menu:close")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_unresolved_list_keyboard(items: List[UnresolvedQuery]) -> InlineKeyboardMarkup:
    """Renders unresolved knowledge items as interactive buttons."""
    keyboard = []
    for item in items:
        title = item.query_text.strip().replace("\n", " ")
        if len(title) > 30:
            title = title[:27] + "..."
        btn_text = f"❓ {title}"
        keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"unresolved_view:{item.id}")])

    if not items:
        keyboard.append([InlineKeyboardButton(text="✅ Hamma savollarga yechim topilgan", callback_data="menu:refresh_settings")])

    keyboard.append([InlineKeyboardButton(text="⬅️ Bosh menyuga qaytish", callback_data="menu:refresh_settings")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_unresolved_detail_keyboard(query_id: int) -> InlineKeyboardMarkup:
    """Actions keyboard for a specific unresolved knowledge item."""
    keyboard = [
        [
            InlineKeyboardButton(text="✍️ Yechim kiritish (O'rgatish)", callback_data=f"unresolved_teach:{query_id}"),
            InlineKeyboardButton(text="🗑 Keraksiz / O'chirish", callback_data=f"unresolved_dismiss:{query_id}")
        ],
        [
            InlineKeyboardButton(text="⬅️ Ro'yxatga qaytish", callback_data="menu:unresolved_queue")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_recent_messages_keyboard(messages: List[TelegramMessage]) -> InlineKeyboardMarkup:
    """Renders recent incoming messages from groups/chats."""
    keyboard = []
    for msg in messages[:8]:
        text_preview = (msg.text or msg.media_type or "Fayl").strip().replace("\n", " ")
        if len(text_preview) > 25:
            text_preview = text_preview[:22] + "..."
        sender = (msg.sender_name or "Foydalanuvchi").split()[0]
        btn_text = f"💬 {sender}: {text_preview}"
        keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"msg_view:{msg.id}")])

    keyboard.append([InlineKeyboardButton(text="⬅️ Bosh menyuga qaytish", callback_data="menu:refresh_settings")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_group_item_keyboard(groups: List[TelegramGroup]) -> InlineKeyboardMarkup:
    """Builds keyboard listing all monitored groups."""
    keyboard = []
    for g in groups:
        l_status = "🟢" if g.learning_enabled else "🔴"
        r_status = "💬" if g.reply_enabled else "🔇"
        button_text = f"{l_status} {r_status} {g.title[:25]}"
        keyboard.append([InlineKeyboardButton(text=button_text, callback_data=f"group_cfg:{g.chat_id}")])

    keyboard.append([InlineKeyboardButton(text="⬅️ Sozlamalarga qaytish", callback_data="menu:refresh_settings")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_group_settings_keyboard(
    chat_id: int,
    group_title: str,
    learning_on: bool,
    reply_on: bool
) -> InlineKeyboardMarkup:
    """Settings keyboard for a specific group."""
    l_text = "🟢 O'rganish: ON" if learning_on else "🔴 O'rganish: OFF"
    r_text = "🟢 Javob berish: ON" if reply_on else "🔴 Javob berish: OFF (Jim turadi)"

    keyboard = [
        [InlineKeyboardButton(text=l_text, callback_data=f"grp_toggle_learn:{chat_id}")],
        [InlineKeyboardButton(text=r_text, callback_data=f"grp_toggle_reply:{chat_id}")],
        [InlineKeyboardButton(text="⬅️ Guruhlar ro'yxatiga qaytish", callback_data="menu:groups")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_confirmation_keyboard(action_name: str) -> InlineKeyboardMarkup:
    """Confirmation keyboard for destructive actions."""
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"confirm:{action_name}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel:action")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_feedback_keyboard(knowledge_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """Optional thumbs up / down feedback buttons."""
    kid = knowledge_id or 0
    keyboard = [
        [
            InlineKeyboardButton(text="👍", callback_data=f"fb:up:{kid}"),
            InlineKeyboardButton(text="👎", callback_data=f"fb:down:{kid}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
