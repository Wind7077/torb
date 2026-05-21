import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
BRIDGES_BASE_URL = 'https://raw.githubusercontent.com/Wind7077/torb/main/bridges'

BOT_TOKEN = os.environ['TG_BOT_TOKEN']
dp = Dispatcher()

BRIDGE_TYPES = {
    'mixed':     '🌀 Mixed (лучшие)',
    'obfs4':     '🔵 obfs4',
    'vanilla':   '🟢 Vanilla',
    'webtunnel': '🟣 WebTunnel',
}


def main_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text='🧅 Дать мосты', callback_data='show_types')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def types_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f'bridges:{key}')]
        for key, label in BRIDGE_TYPES.items()
    ]
    buttons.append([InlineKeyboardButton(text='« Назад', callback_data='back')])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def fetch_bridges(bridge_type: str) -> str:
    import aiohttp
    url = f'{BRIDGES_BASE_URL}/{bridge_type}.txt'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    return await r.text()
                return None
    except Exception:
        return None


def format_bridges(text: str, bridge_type: str) -> str:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return '❌ Список пустой'
    label = BRIDGE_TYPES[bridge_type]
    result = f'<b>{label}</b>\n\n'
    result += '<code>'
    result += '\n\n'.join(lines)
    result += '</code>'
    result += f'\n\n<i>Мостов: {len(lines)} • Обновляется каждые 2 часа</i>'
    return result


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        '🧅 <b>Tor Bridges Bot</b>\n\n'
        'Актуальные рабочие мосты для Tor.\n'
        'Обновляются автоматически каждые 2 часа.\n\n'
        'Нажми кнопку чтобы получить мосты 👇',
        reply_markup=main_keyboard(),
        parse_mode=ParseMode.HTML
    )


@dp.callback_query(F.data == 'show_types')
async def show_types(callback: CallbackQuery):
    await callback.message.edit_text(
        '🧅 <b>Выбери тип мостов:</b>\n\n'
        '🌀 <b>Mixed</b> — лучшие мосты всех типов\n'
        '🔵 <b>obfs4</b> — маскируется под случайный протокол\n'
        '🟢 <b>Vanilla</b> — обычные Tor мосты\n'
        '🟣 <b>WebTunnel</b> — маскируется под HTTPS трафик',
        reply_markup=types_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@dp.callback_query(F.data.startswith('bridges:'))
async def send_bridges(callback: CallbackQuery):
    bridge_type = callback.data.split(':')[1]
    await callback.answer('⏳ Загружаю...')

    text = await fetch_bridges(bridge_type)

    if text is None:
        await callback.message.answer(
            '❌ Не удалось загрузить мосты. Попробуй позже.',
            reply_markup=main_keyboard()
        )
        return

    formatted = format_bridges(text, bridge_type)

    # Telegram лимит 4096 символов — если длиннее, шлём частями
    if len(formatted) <= 4096:
        await callback.message.answer(
            formatted,
            parse_mode=ParseMode.HTML,
            reply_markup=main_keyboard()
        )
    else:
        # Шлём мосты без форматирования если слишком длинно
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        label = BRIDGE_TYPES[bridge_type]
        chunk = f'{label}\n\n'
        for line in lines:
            if len(chunk) + len(line) + 2 > 4000:
                await callback.message.answer(f'<code>{chunk}</code>',
                                              parse_mode=ParseMode.HTML)
                chunk = ''
            chunk += line + '\n\n'
        if chunk.strip():
            await callback.message.answer(
                f'<code>{chunk}</code>',
                parse_mode=ParseMode.HTML,
                reply_markup=main_keyboard()
            )

    await callback.answer()


@dp.callback_query(F.data == 'back')
async def go_back(callback: CallbackQuery):
    await callback.message.edit_text(
        '🧅 <b>Tor Bridges Bot</b>\n\n'
        'Актуальные рабочие мосты для Tor.\n'
        'Обновляются автоматически каждые 2 часа.\n\n'
        'Нажми кнопку чтобы получить мосты 👇',
        reply_markup=main_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
