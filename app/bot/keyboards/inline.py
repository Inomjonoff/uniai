"""
Inline Keyboards for Telegram Bot.
"""
from typing import List, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.db.models import TelegramGroup


def get_settings_keyboard(
    groups_count: int,
    knowledge_count: int,
    auto_learning: bool = True,
    screenshot_analysis: bool = True
) -> InlineKeyboardMarkup:
    """Builds interactive main settings keyboard."""
    learn_icon = "🟢 ON" if auto_learning else "🔴 OFF"
    vision_icon = "🟢 ON" if screenshot_analysis else "🔴 OFF"

    keyboard = [
        [
            InlineKeyboardButton(text=f"Auto Learning: {learn_icon}", callback_data="toggle:auto_learning"),
            InlineKeyboardButton(text=f"Screenshot Vision: {vision_icon}", callback_data="toggle:screenshot_analysis")
        ],
        [
            InlineKeyboardButton(text=f"👥 Guruhlar ({groups_count})", callback_data="menu:groups"),
            InlineKeyboardButton(text=f"📚 Bilimlar ({knowledge_count:,})", callback_data="menu:knowledge_stats")
        ],
        [
            InlineKeyboardButton(text="🔄 Yangilash", callback_data="menu:refresh_settings"),
            InlineKeyboardButton(text="✖️ Yopish", callback_data="menu:close")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_group_item_keyboard(groups: List[TelegramGroup]) -> InlineKeyboardMarkup:
    """Builds keyboard listing all active groups."""
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
    l_text = "🟢 Learning: ON" if learning_on else "🔴 Learning: OFF"
    r_text = "🟢 Reply: ON" if reply_on else "🔴 Reply: OFF (Jim turadi)"

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
