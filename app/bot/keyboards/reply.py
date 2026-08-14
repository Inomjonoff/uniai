"""
Reply Keyboards for Telegram Bot.
Provides persistent quick-access buttons at the bottom of the chat.
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Builds persistent main menu reply keyboard."""
    keyboard = [
        [
            KeyboardButton(text="⚙️ Boshqaruv paneli"),
            KeyboardButton(text="🎓 O'rganish kutilayotganlar")
        ],
        [
            KeyboardButton(text="👥 Guruhlarni boshqarish"),
            KeyboardButton(text="📨 Oxirgi murojaatlar")
        ],
        [
            KeyboardButton(text="📚 Bilimlar statistikasi"),
            KeyboardButton(text="✍️ Qoida / Topshiriq berish")
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        persistent=True,
        input_field_placeholder="Savol yoki topshiriq yozing..."
    )
