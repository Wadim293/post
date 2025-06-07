import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ChatJoinRequest, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from config import BOT_TOKEN, CHANNEL_ID, ADMIN_IDS
from database import UserMessageLog, VisitStats, GreetingText
from facebook import send_fb_event
from tortoise.exceptions import IntegrityError

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(storage=MemoryStorage())


class GreetingEdit(StatesGroup):
    waiting_for_text = State()


@dp.chat_join_request()
async def handle_join(event: ChatJoinRequest):
    user = event.from_user
    ref = event.invite_link.name if event.invite_link else "unknown"

    # ✅ Пытаемся одобрить заявку
    try:
        await bot.approve_chat_join_request(chat_id=event.chat.id, user_id=user.id)
    except Exception as e:
        print(f"[TG] Не удалось одобрить заявку {user.id}: {e}")

    # ✅ Отправляем приветствие
    try:
        greeting = await GreetingText.first()
        if greeting and greeting.enabled:
            await bot.send_message(chat_id=user.id, text=greeting.text)
        await UserMessageLog.create(telegram_id=user.id)
    except IntegrityError:
        print(f"[DB] Пользователь {user.id} уже в базе.")
    except Exception as e:
        print(f"[ERROR] Сообщение не доставлено {user.id}: {e}")

    await VisitStats.create(ref=ref, joined=True)
    await asyncio.get_event_loop().run_in_executor(None, send_fb_event, user.id, ref)

    print(f"[TG] Approved {user.id}, ref={ref}")


async def send_stats_message(chat_id: int):
    visits = await VisitStats.filter(visited=True).count()
    clicks = await VisitStats.filter(clicked=True).count()
    joins = await VisitStats.filter(joined=True).count()

    greeting = await GreetingText.first()
    enabled = greeting.enabled if greeting else False
    toggle_text = "🟢 Приветствие вкл" if enabled else "🔴 Приветствие выкл"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Обновить", callback_data="refresh_stats")],
        [InlineKeyboardButton(text="Изменить приветствие", callback_data="edit_greeting")],
        [InlineKeyboardButton(text=toggle_text, callback_data="toggle_greeting")]
    ])

    await bot.send_message(
        chat_id=chat_id,
        text=(
            f"<b>📊 Статистика:</b>\n"
            f"<blockquote>"
            f"• <b>Визитов:</b> <b>{visits}</b>\n"
            f"• <b>Нажали кнопку:</b> <b>{clicks}</b>\n"
            f"• <b>Подписались:</b> <b>{joins}</b>"
            f"</blockquote>"
        ),
        reply_markup=kb
    )


@dp.message(F.text == "/start")
async def handle_start(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        await send_stats_message(message.chat.id)


@dp.message(F.text == "/webtop")
async def handle_webtop(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await send_stats_message(message.chat.id)


@dp.callback_query(F.data == "refresh_stats")
async def handle_refresh(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return await callback.answer("Нет доступа", show_alert=True)
    try:
        await callback.message.delete()
    except Exception as e:
        print(f"[ERROR] Не удалось удалить сообщение: {e}")
    await send_stats_message(callback.message.chat.id)


@dp.callback_query(F.data == "edit_greeting")
async def handle_edit_greeting(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return await callback.answer("Нет доступа", show_alert=True)

    try:
        await callback.message.delete()
    except Exception:
        pass

    greeting = await GreetingText.first()
    text = greeting.text if greeting else "Текст не задан."

    await bot.send_message(
        callback.message.chat.id,
        f"<b>Текущий текст приветствия:</b>\n\n<pre>{text}</pre>\n\n"
        "Отправь новый текст для приветствия:",
        parse_mode="HTML"
    )

    await state.set_state(GreetingEdit.waiting_for_text)


@dp.message(GreetingEdit.waiting_for_text)
async def update_greeting_text(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return

    text = message.text.strip()
    greeting = await GreetingText.first()
    if greeting:
        greeting.text = text
        await greeting.save()
    else:
        await GreetingText.create(text=text)

    await message.answer("✅ Приветствие обновлено.")
    await state.clear()


@dp.callback_query(F.data == "toggle_greeting")
async def handle_toggle_greeting(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return await callback.answer("Нет доступа", show_alert=True)

    greeting = await GreetingText.first()
    if greeting:
        greeting.enabled = not greeting.enabled
        await greeting.save()
        state = "🟢 Приветствие вкл" if greeting.enabled else "🔴 Приветствие выкл"
        await callback.answer(f"Приветствие {'включено' if greeting.enabled else 'отключено'}")
    else:
        greeting = await GreetingText.create(text="🎉 Спасибо за подписку!", enabled=True)
        state = "🟢 Приветствие вкл"
        await callback.answer("Приветствие включено (по умолчанию)")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Обновить", callback_data="refresh_stats")],
        [InlineKeyboardButton(text="Изменить приветствие", callback_data="edit_greeting")],
        [InlineKeyboardButton(text=state, callback_data="toggle_greeting")]
    ])

    try:
        await callback.message.edit_reply_markup(reply_markup=kb)
    except Exception as e:
        print(f"[ERROR] Не удалось обновить кнопки: {e}")