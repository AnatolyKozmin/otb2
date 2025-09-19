import asyncio
import json
import logging
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()


# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.getenv('TOKEN')
ADDRESS = "Вешняковский проезд"

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Загрузка данных
def load_data():
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"users": {}, "slots": {}, "last_update": ""}

def save_data(data):
    data['last_update'] = datetime.now().isoformat()
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Генерация слотов для дат
def generate_slots_for_dates():
    """Генерирует слоты для всех дат с рандомной доступностью"""
    data = load_data()
    
    # Даты с днями недели
    dates = [
        "01.10.2025(пн)", "02.10.2025(вт)", "03.10.2025(ср)", 
        "04.10.2025(чт)", "05.10.2025(пт)", "06.10.2025(сб)", "07.10.2025(вск)"
    ]
    
    # Временные слоты
    time_slots = [
        "10:00 - 11:00", "11:00 - 12:00", "12:00 - 13:00", "13:00 - 14:00",
        "14:00 - 15:00", "15:00 - 16:00", "16:00 - 17:00", "17:00 - 18:00",
        "18:00 - 19:00", "19:00 - 20:00", "20:00 - 21:00"
    ]
    
    # Генерируем слоты только если их еще нет
    if not data['slots']:
        for date in dates:
            for time_slot in time_slots:
                slot_key = f"{date}_{time_slot}".replace("(", "").replace(")", "").replace(".", "_").replace(" ", "_").replace("-", "_")
                
                # Рандомная доступность от 0 до 3 мест
                max_capacity = random.randint(0, 3)
                
                data['slots'][slot_key] = {
                    'date': date,
                    'time': time_slot,
                    'users': [],
                    'max_capacity': max_capacity
                }
        
        save_data(data)
    
    return data

# Команды бота
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Создаем клавиатуру с основными кнопками
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="📅 Запись на слоты"))
    builder.add(types.KeyboardButton(text="📋 Мои записи"))
    builder.adjust(2)
    
    await message.answer(
        "👋 Добро пожаловать! Я бот для записи на собеседования.\n\n"
        "📅 <b>Запись на слоты</b> - выбрать дату и время для записи\n"
        "📋 <b>Мои записи</b> - посмотреть ваши текущие записи\n\n"
        "Выберите действие:",
        reply_markup=builder.as_markup(resize_keyboard=True),
        parse_mode="HTML"
    )

@dp.message(lambda message: message.text == "📅 Запись на слоты")
@dp.message(Command("slots"))
async def cmd_slots(message: types.Message):
    data = generate_slots_for_dates()
    
    # Собираем уникальные даты
    dates = sorted(list({slot['date'] for slot in data['slots'].values()}))
    
    if not dates:
        await message.answer("Нет доступных дат для записи.")
        return
    
    # Создаем инлайн-кнопки с датами
    builder = InlineKeyboardBuilder()
    for date in dates:
        builder.button(text=date, callback_data=f"date_{date}")
    builder.adjust(2)
    
    await message.answer(
        "📅 Выберите дату для записи на собеседование:",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(lambda c: c.data.startswith('date_'))
async def select_date(callback: types.CallbackQuery):
    selected_date = callback.data.replace('date_', '')
    data = load_data()
    
    # Собираем доступные временные слоты для выбранной даты
    available_slots = []
    for slot_key, slot in data['slots'].items():
        if slot['date'] == selected_date:
            free_places = slot['max_capacity'] - len(slot['users'])
            if free_places > 0:  # Показываем только слоты со свободными местами
                available_slots.append((slot_key, slot['time'], free_places))
    
    if not available_slots:
        await callback.message.edit_text("❌ Нет свободных слотов на выбранную дату")
        return
    
    # Создаем клавиатуру со временем
    builder = InlineKeyboardBuilder()
    for slot_key, time, free_places in available_slots:
        builder.button(
            text=f"⏰ {time} ({free_places} мест)",
            callback_data=f"slot_{slot_key}"
        )
    
    builder.button(text="◀️ Назад к датам", callback_data="back_to_dates")
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"📅 <b>{selected_date}</b>\n\n"
        "⏰ Выберите время для записи:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@dp.callback_query(lambda c: c.data == "back_to_dates")
async def back_to_dates(callback: types.CallbackQuery):
    # Возвращаемся к выбору дат
    data = load_data()
    dates = sorted(list({slot['date'] for slot in data['slots'].values()}))
    
    builder = InlineKeyboardBuilder()
    for date in dates:
        builder.button(text=date, callback_data=f"date_{date}")
    builder.adjust(2)
    
    await callback.message.edit_text(
        "📅 Выберите дату для записи на собеседование:",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(lambda c: c.data.startswith('slot_'))
async def select_slot(callback: types.CallbackQuery):
    slot_key = callback.data.replace('slot_', '')
    data = load_data()
    
    if slot_key not in data['slots']:
        await callback.answer("❌ Слот не найден")
        return
    
    slot = data['slots'][slot_key]
    free_slots = slot['max_capacity'] - len(slot['users'])
    
    if free_slots <= 0:
        await callback.answer("❌ Нет свободных мест в этом слоте")
        return
    
    # Проверяем, есть ли уже запись у пользователя
    user_id = str(callback.from_user.id)
    if user_id in data['users'] and data['users'][user_id]:
        await callback.answer("❌ У вас уже есть запись. Сначала отмените текущую запись.")
        return
    
    # Показываем подтверждение
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить запись", callback_data=f"confirm_{slot_key}")
    builder.button(text="❌ Отмена", callback_data="back_to_dates")
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"📋 <b>Подтверждение записи</b>\n\n"
        f"📅 <b>Дата:</b> {slot['date']}\n"
        f"⏰ <b>Время:</b> {slot['time']}\n"
        f"📍 <b>Адрес:</b> {ADDRESS}\n"
        f"👤 <b>Имя:</b> {callback.from_user.full_name}\n\n"
        f"⚠️ <b>Важно:</b> Отменить запись можно не ранее чем за 24 часа до начала собеседования.\n\n"
        f"Подтверждаете запись?",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@dp.callback_query(lambda c: c.data.startswith('confirm_'))
async def confirm_booking(callback: types.CallbackQuery):
    slot_key = callback.data.replace('confirm_', '')
    data = load_data()
    
    if slot_key not in data['slots']:
        await callback.answer("❌ Слот не найден")
        return
    
    slot = data['slots'][slot_key]
    user_id = str(callback.from_user.id)
    user_name = callback.from_user.full_name
    
    # Проверяем еще раз доступность
    free_slots = slot['max_capacity'] - len(slot['users'])
    if free_slots <= 0:
        await callback.answer("❌ Нет свободных мест в этом слоте")
        return
    
    # Проверяем, есть ли уже запись у пользователя
    if user_id in data['users'] and data['users'][user_id]:
        await callback.answer("❌ У вас уже есть запись")
        return
    
    # Записываем пользователя
    if user_id not in data['users']:
        data['users'][user_id] = {}
    
    data['users'][user_id] = {
        'slot_key': slot_key,
        'date': slot['date'],
        'time': slot['time'],
        'timestamp': datetime.now().isoformat(),
        'user_name': user_name
    }
    
    slot['users'].append({
        'name': user_name,
        'user_id': user_id,
        'timestamp': datetime.now().isoformat()
    })
    
    save_data(data)
    
    await callback.answer("✅ Запись подтверждена!")
    await callback.message.edit_text(
        f"✅ <b>Запись подтверждена!</b>\n\n"
        f"📅 <b>Дата:</b> {slot['date']}\n"
        f"⏰ <b>Время:</b> {slot['time']}\n"
        f"📍 <b>Адрес:</b> {ADDRESS}\n"
        f"👤 <b>Имя:</b> {user_name}\n"
        f"📊 <b>Свободных мест осталось:</b> {free_slots - 1}\n\n"
        "Чтобы посмотреть вашу запись, используйте кнопку 'Мои записи'",
        parse_mode="HTML"
    )

@dp.message(lambda message: message.text == "📋 Мои записи")
@dp.message(Command("my_records"))
async def cmd_my_records(message: types.Message):
    data = load_data()
    user_id = str(message.from_user.id)
    
    if user_id not in data['users'] or not data['users'][user_id]:
        await message.answer("📝 У вас нет активных записей")
        return
    
    record = data['users'][user_id]
    
    # Проверяем, можно ли отменить запись (за 24 часа)
    can_cancel = True
    try:
        # Пытаемся распарсить дату и время
        date_str = record['date'].split('(')[0]  # Убираем день недели
        time_str = record['time'].split(' - ')[0]  # Берем только время начала
        
        # Парсим дату и время
        appointment_dt = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
        now = datetime.now()
        
        if appointment_dt - now < timedelta(hours=24):
            can_cancel = False
    except:
        pass  # Если не удалось распарсить, разрешаем отмену
    
    response = (
        f"📋 <b>Ваша запись:</b>\n\n"
        f"📅 <b>Дата:</b> {record['date']}\n"
        f"⏰ <b>Время:</b> {record['time']}\n"
        f"📍 <b>Адрес:</b> {ADDRESS}\n"
        f"👤 <b>Имя:</b> {record['user_name']}\n"
    )
    
    if not can_cancel:
        response += "\n⚠️ <b>Отмена недоступна:</b> менее 24 часов до собеседования"
    
    # Добавляем кнопку для отмены записи
    builder = InlineKeyboardBuilder()
    if can_cancel:
        builder.button(text="❌ Отменить запись", callback_data="cancel_booking")
    else:
        builder.button(text="❌ Отмена недоступна", callback_data="no_cancel")
    
    await message.answer(response, reply_markup=builder.as_markup(), parse_mode="HTML")

@dp.callback_query(lambda c: c.data == "cancel_booking")
async def cancel_booking(callback: types.CallbackQuery):
    data = load_data()
    user_id = str(callback.from_user.id)
    
    if user_id not in data['users'] or not data['users'][user_id]:
        await callback.answer("❌ Нет записи для отмены")
        return
    
    record = data['users'][user_id]
    
    # Показываем подтверждение отмены
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, отменить", callback_data="confirm_cancel")
    builder.button(text="❌ Нет, оставить", callback_data="keep_booking")
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"⚠️ <b>Подтверждение отмены</b>\n\n"
        f"Вы действительно хотите отменить запись?\n\n"
        f"📅 <b>Дата:</b> {record['date']}\n"
        f"⏰ <b>Время:</b> {record['time']}\n\n"
        f"После отмены вы сможете записаться на другое время.",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@dp.callback_query(lambda c: c.data == "confirm_cancel")
async def confirm_cancel(callback: types.CallbackQuery):
    data = load_data()
    user_id = str(callback.from_user.id)
    
    if user_id not in data['users'] or not data['users'][user_id]:
        await callback.answer("❌ Нет записи для отмены")
        return
    
    record = data['users'][user_id]
    slot_key = record['slot_key']
    
    # Удаляем пользователя из слота
    if slot_key in data['slots']:
        data['slots'][slot_key]['users'] = [
            u for u in data['slots'][slot_key]['users'] 
            if u.get('user_id') != user_id
        ]
    
    # Удаляем запись пользователя
    del data['users'][user_id]
    save_data(data)
    
    await callback.message.edit_text(
        f"✅ <b>Запись отменена!</b>\n\n"
        f"📅 <b>Отмененная дата:</b> {record['date']}\n"
        f"⏰ <b>Отмененное время:</b> {record['time']}\n\n"
        f"Теперь вы можете записаться на другое время.",
        parse_mode="HTML"
    )

@dp.callback_query(lambda c: c.data == "keep_booking")
async def keep_booking(callback: types.CallbackQuery):
    # Возвращаемся к просмотру записи
    await cmd_my_records(callback.message)

@dp.callback_query(lambda c: c.data == "no_cancel")
async def no_cancel(callback: types.CallbackQuery):
    await callback.answer("⚠️ Отмена недоступна менее чем за 24 часа", show_alert=True)

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "🤖 <b>Команды бота:</b>\n\n"
        "📅 <b>Запись на слоты</b> - выбрать дату и время для записи на собеседование\n"
        "📋 <b>Мои записи</b> - посмотреть вашу текущую запись\n"
        "❓ <b>/help</b> - показать эту справку\n\n"
        "📍 <b>Адрес:</b> {ADDRESS}\n\n"
        "⚠️ <b>Важно:</b> Отменить запись можно не ранее чем за 24 часа до начала собеседования.\n"
        "У одного пользователя может быть только одна активная запись.",
        parse_mode="HTML"
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())