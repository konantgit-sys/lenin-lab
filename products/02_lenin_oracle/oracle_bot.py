#!/usr/bin/env python3
"""
Lenin Oracle Telegram Bot
@lenin_oracle_bot — ask Lenin, get a real quote.
Powered by FAISS semantic search on 169K paragraphs.
"""

import asyncio
import sys
import os
import time
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

sys.path.insert(0, os.path.dirname(__file__))
from oracle_engine import search, format_response, get_random_quote, get_stats

# Config
BOT_TOKEN = "8668283959:AAH6VlbqUnCM7WKzsIgs8Eodrayy4Hgtmzw"
STATS_DB = os.path.join(os.path.dirname(__file__), "oracle_stats.db")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def log_query(user_id: int, username: str, query: str, results: int):
    """Log usage statistics."""
    conn = sqlite3.connect(STATS_DB)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            query TEXT,
            results INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    conn.execute(
        "INSERT INTO queries (user_id, username, query, results) VALUES (?, ?, ?, ?)",
        (user_id, username, query, results),
    )
    conn.commit()
    conn.close()


# --- Handlers ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "⚡ <b>Ленин-Оракул</b>\n\n"
        "Задайте любой вопрос — я найду реальные цитаты Ленина из 55 томов (169 000+ параграфов).\n\n"
        "Никаких нейросетевых галлюцинаций — только подлинные слова, с указанием тома и года.\n\n"
        "<b>Команды:</b>\n"
        "/ask вопрос — спросить Ленина\n"
        "/random — случайная цитата\n"
        "/stats — статистика корпуса\n"
        "/help — помощь",
        parse_mode="HTML",
    )


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "<b>Как пользоваться:</b>\n\n"
        "1. Пишите вопрос прямо в чат\n"
        "2. Или используйте команду /ask\n"
        "3. Я нахожу 2-5 реальных цитат Ленина\n"
        "4. Каждая цитата — с томом и годом\n\n"
        "<b>Примеры:</b>\n"
        "• Что Ленин думал о кооперации?\n"
        "• Ленин о государстве\n"
        "• Отношение Ленина к войне\n\n"
        "Кнопка «Ещё цитата» — альтернативный взгляд.\n"
        "Кнопка «Случайная» — открыть на любой странице.",
        parse_mode="HTML",
    )


@dp.message(Command("random"))
async def cmd_random(message: types.Message):
    await message.answer_chat_action("typing")
    quote = get_random_quote()
    text = f"📖 <b>Случайная цитата</b>\n\n"
    text += f"{quote.year} г., том {quote.volume}\n"
    text += f"«{quote.text}»"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Ещё случайную", callback_data="random")],
        [InlineKeyboardButton(text="🔍 Искать по теме", switch_inline_query_current_chat="")],
    ])
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    stats = get_stats()
    conn = sqlite3.connect(STATS_DB)
    total_queries = conn.execute("SELECT COUNT(*) FROM queries").fetchone()[0]
    conn.close()
    await message.answer(
        f"📊 <b>Статистика корпуса Ленина</b>\n\n"
        f"📚 Параграфов: {stats['total_paragraphs']:,}\n"
        f"📅 Период: {stats['year_from']}–{stats['year_to']}\n"
        f"💬 Размеченных цитат: {stats['scored_quotes']:,}\n"
        f"🔍 FAISS-векторов: 93 711\n"
        f"⚡ Запросов к боту: {total_queries}",
        parse_mode="HTML",
    )


@dp.message(Command("ask"))
async def cmd_ask(message: types.Message):
    query = message.text.replace("/ask", "").strip()
    if not query:
        await message.answer("Напишите вопрос после /ask. Например: /ask Что Ленин думал о демократии?")
        return
    await process_query(message, query)


@dp.message(F.text & ~F.text.startswith("/"))
async def handle_any_text(message: types.Message):
    """Treat any non-command text as a question."""
    query = message.text.strip()
    if len(query) < 3:
        await message.answer("Задайте вопрос подлиннее — хотя бы 3 символа.")
        return
    await process_query(message, query)


@dp.callback_query(F.data == "random")
async def cb_random(callback: types.CallbackQuery):
    quote = get_random_quote()
    text = f"📖 <b>Случайная цитата</b>\n\n"
    text += f"{quote.year} г., том {quote.volume}\n"
    text += f"«{quote.text}»"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Ещё случайную", callback_data="random")],
        [InlineKeyboardButton(text="🔍 Искать по теме", switch_inline_query_current_chat="")],
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@dp.callback_query(F.data.startswith("more:"))
async def cb_more(callback: types.CallbackQuery):
    query = callback.data.split(":", 1)[1]
    await callback.message.answer_chat_action("typing")
    results = search(query, k=3)
    response_text = format_response(results, query)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Другая позиция", callback_data=f"alt:{query}")],
        [InlineKeyboardButton(text="🎲 Случайная", callback_data="random")],
    ])
    await callback.message.reply(response_text[:4000], reply_markup=kb)


@dp.callback_query(F.data.startswith("alt:"))
async def cb_alt(callback: types.CallbackQuery):
    query = callback.data.split(":", 1)[1]
    await callback.message.answer_chat_action("typing")
    # Search with different indices by using offset
    results = search(query, k=5)
    # Skip first 2 for variety
    response_text = format_response(results[2:], query)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Ещё варианты", callback_data=f"more:{query}")],
        [InlineKeyboardButton(text="🎲 Случайная", callback_data="random")],
    ])
    await callback.message.reply(response_text[:4000], reply_markup=kb)


# --- Core ---

async def process_query(message: types.Message, query: str):
    """Process a user question."""
    await message.answer_chat_action("typing")

    try:
        results = search(query, k=5)
    except Exception as e:
        await message.answer(f"⚠️ Ошибка поиска: {e}")
        return

    log_query(message.from_user.id, message.from_user.username or "", query, len(results))

    if not results:
        await message.answer(
            "🔍 Не нашёл точных цитат по вашему запросу.\n\n"
            "Попробуйте:\n"
            "• Переформулировать вопрос\n"
            "• Использовать другие слова\n"
            "• Спросить про конкретный период или тему",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎲 Случайная цитата", callback_data="random")],
            ]),
        )
        return

    response_text = format_response(results, query)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Другая позиция", callback_data=f"alt:{query}")],
        [InlineKeyboardButton(text="📖 Ещё цитаты", callback_data=f"more:{query}")],
        [InlineKeyboardButton(text="🎲 Случайная", callback_data="random")],
    ])
    await message.answer(response_text[:4000], reply_markup=kb)


async def main():
    print("⚡ Lenin Oracle Bot starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
