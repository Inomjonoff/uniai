"""
Telegram Bot handlers registration package.
"""
from aiogram import Router
from app.bot.handlers.private import private_router
from app.bot.handlers.group import group_router
from app.bot.handlers.admin import admin_router
from app.bot.handlers.callbacks import callback_router

main_router = Router()
main_router.include_router(admin_router)
main_router.include_router(callback_router)
main_router.include_router(private_router)
main_router.include_router(group_router)

__all__ = ["main_router", "private_router", "group_router", "admin_router", "callback_router"]
