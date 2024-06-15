import logging
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import (
    ParseMode,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile,
)
from aiogram.utils import executor
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from datetime import datetime, timedelta
import pandas as pd
import os

API_TOKEN = os.getenv("API_TOKEN")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
PHONE_NUMBER = os.getenv("PHONE_NUMBER")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())

# Initialize SQLite connection
conn = sqlite3.connect("bookings.db", check_same_thread=False)
cur = conn.cursor()

# Create table if it doesn't exist
cur.execute(
    """
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team_name TEXT,
        date DATE,
        time TEXT
    )
"""
)
conn.commit()

# Constants for time slots and emojis
TIME_SLOTS = [
    {"time": "05:00-06:00", "emoji": "🌞"},
    {"time": "06:00-07:00", "emoji": "🌞"},
    {"time": "07:00-08:00", "emoji": "🌞"},
    {"time": "08:00-09:00", "emoji": "🌞"},
    {"time": "09:00-10:00", "emoji": "🌞"},
    {"time": "10:00-11:00", "emoji": "🌞"},
    {"time": "11:00-12:00", "emoji": "🌞"},
    {"time": "12:00-13:00", "emoji": "🌞"},
    {"time": "13:00-14:00", "emoji": "🌞"},
    {"time": "14:00-15:00", "emoji": "🌞"},
    {"time": "15:00-16:00", "emoji": "🌞"},
    {"time": "16:00-17:00", "emoji": "🌞"},
    {"time": "17:00-18:00", "emoji": "🌞"},
    {"time": "18:00-19:00", "emoji": "🌞"},
    {"time": "19:00-20:00", "emoji": "🌞"},
    {"time": "20:00-21:00", "emoji": "🌙"},
    {"time": "21:00-22:00", "emoji": "🌙"},
    {"time": "22:00-23:00", "emoji": "🌙"},
    {"time": "23:00-00:00", "emoji": "🌙"},
    {"time": "00:00-01:00", "emoji": "🌙"},
    {"time": "01:00-02:00", "emoji": "🌙"},
]


class BookingState(StatesGroup):
    team_name = State()
    date = State()
    time = State()


class AdminBookingState(StatesGroup):
    action = State()
    booking_id = State()
    team_name = State()
    date = State()
    time = State()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def generate_date_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup()
    today = datetime.now().date()
    for i in range(7):
        date = today + timedelta(days=i)
        button = InlineKeyboardButton(
            date.strftime("%Y-%m-%d (%A)"), callback_data=f"date:{date}"
        )
        keyboard.add(button)
    return keyboard


def generate_time_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup()
    for slot in TIME_SLOTS:
        button = InlineKeyboardButton(
            f"{slot['emoji']} {slot['time']}", callback_data=f"time:{slot['time']}"
        )
        keyboard.add(button)
    return keyboard


@dp.message_handler(commands=["start"])
async def send_welcome(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["View Bookings"]
    if is_admin(message.from_user.id):
        buttons.extend(
            [
                "Add Booking",
                "Update Booking",
                "Delete Booking",
                "View Statistics",
                "Export Data",
            ]
        )
    keyboard.add(*buttons)
    await message.answer(
        "Welcome! Use the menu to manage bookings.", reply_markup=keyboard
    )


@dp.message_handler(lambda message: message.text == "View Bookings")
async def show_bookings(message: types.Message):
    today = datetime.now().date()
    next_week = today + timedelta(days=7)

    # Fetch bookings and convert date strings to date objects
    cur.execute(
        "SELECT id, date, time, team_name FROM bookings WHERE date BETWEEN ? AND ?",
        (today, next_week),
    )
    bookings = cur.fetchall()
    booking_dict = {}
    for booking in bookings:
        booking_date = datetime.strptime(booking[1], "%Y-%m-%d").date()
        if booking_date not in booking_dict:
            booking_dict[booking_date] = []
        booking_dict[booking_date].append((booking[2], booking[3], booking[0]))

    message_text = "Available and booked times for the next week:\n"
    for single_date in (
        today + timedelta(n) for n in range((next_week - today).days + 1)
    ):
        date_str = single_date.strftime("%Y-%m-%d (%A)")
        if single_date in booking_dict:
            message_text += f"\n<strong>{date_str}</strong>\n"
            for slot in TIME_SLOTS:
                if slot["time"] in [
                    booking[0] for booking in booking_dict[single_date]
                ]:
                    for booking_info in booking_dict[single_date]:
                        if booking_info[0] == slot["time"]:
                            id_, team_name = booking_info[2], booking_info[1]
                            if is_admin(message.from_user.id):
                                message_text += f"{slot['emoji']} {slot['time']} ❌ id: {id_}, {team_name}\n"
                            else:
                                message_text += f"{slot['emoji']} {slot['time']} ❌\n"
                            break
                else:
                    message_text += f"{slot['emoji']} {slot['time']}\n"
        else:
            message_text += (
                f"\n<strong>{date_str}</strong>\n"
                + "\n".join([f"{slot['emoji']} {slot['time']}" for slot in TIME_SLOTS])
                + "\n"
            )

    message_text += f"\nFor booking, call: {PHONE_NUMBER}"
    await message.answer(message_text, parse_mode=ParseMode.HTML)


@dp.message_handler(
    lambda message: message.text == "Add Booking" and is_admin(message.from_user.id)
)
async def add_booking(message: types.Message):
    await message.answer("Please provide the Team Name:")
    await AdminBookingState.team_name.set()


@dp.message_handler(state=AdminBookingState.team_name, user_id=ADMIN_IDS)
async def admin_team_name(message: types.Message, state: FSMContext):
    team_name = message.text
    await state.update_data(team_name=team_name)
    await message.answer("Please select a date:", reply_markup=generate_date_keyboard())
    await AdminBookingState.date.set()


@dp.callback_query_handler(
    lambda c: c.data.startswith("date"), state=AdminBookingState.date
)
async def process_date_selection(
    callback_query: types.CallbackQuery, state: FSMContext
):
    selected_date = callback_query.data.split(":")[1]
    await state.update_data(date=selected_date)
    await bot.send_message(
        callback_query.from_user.id,
        "Please select a time:",
        reply_markup=generate_time_keyboard(),
    )
    await AdminBookingState.time.set()


@dp.callback_query_handler(
    lambda c: c.data.startswith("time"), state=AdminBookingState.time
)
async def process_time_selection(
    callback_query: types.CallbackQuery, state: FSMContext
):
    selected_time = callback_query.data.split(":", 1)[1]
    await state.update_data(time=selected_time)
    data = await state.get_data()

    cur.execute(
        "SELECT * FROM bookings WHERE date = ? AND time = ?",
        (data["date"], selected_time),
    )
    existing_booking = cur.fetchone()

    if existing_booking:
        await bot.send_message(
            callback_query.from_user.id,
            "This time slot is already booked. Do you want to update it? (yes/no)",
        )
        await AdminBookingState.next()
    else:
        cur.execute(
            "INSERT INTO bookings (team_name, date, time) VALUES (?, ?, ?)",
            (data["team_name"], data["date"], selected_time),
        )
        conn.commit()
        await bot.send_message(callback_query.from_user.id, "Booking added.")
        await state.finish()


@dp.message_handler(state=AdminBookingState.time)
async def confirm_update(message: types.Message, state: FSMContext):
    if message.text.lower() == "yes":
        data = await state.get_data()
        cur.execute(
            "UPDATE bookings SET team_name = ? WHERE date = ? AND time = ?",
            (data["team_name"], data["date"], data["time"]),
        )
        conn.commit()
        await message.answer("Booking updated.")
    else:
        await message.answer("Booking not updated.")
    await state.finish()


@dp.message_handler(
    lambda message: message.text == "Update Booking" and is_admin(message.from_user.id)
)
async def update_booking(message: types.Message, state: FSMContext):
    await message.answer("Please provide the Booking ID:")
    await AdminBookingState.booking_id.set()
    await state.update_data(action="update booking")


@dp.message_handler(
    lambda message: message.text == "Delete Booking" and is_admin(message.from_user.id)
)
async def delete_booking(message: types.Message, state: FSMContext):
    await message.answer("Please provide the Booking ID:")
    await AdminBookingState.booking_id.set()
    await state.update_data(action="delete booking")


@dp.message_handler(state=AdminBookingState.booking_id, user_id=ADMIN_IDS)
async def admin_booking_id(message: types.Message, state: FSMContext):
    booking_id = int(message.text)
    await state.update_data(booking_id=booking_id)
    data = await state.get_data()
    if data["action"] == "update booking":
        await message.answer("Please provide the new Team Name:")
        await AdminBookingState.team_name.set()
    elif data["action"] == "delete booking":
        cur.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
        conn.commit()
        await message.answer(f"Booking with ID {booking_id} deleted.")
        await state.finish()
    else:
        await message.answer("Invalid action")


@dp.message_handler(state=AdminBookingState.team_name, user_id=ADMIN_IDS)
async def admin_team_name(message: types.Message, state: FSMContext):
    team_name = message.text
    await state.update_data(team_name=team_name)
    await message.answer("Please select a date:", reply_markup=generate_date_keyboard())
    await AdminBookingState.date.set()


@dp.callback_query_handler(
    lambda c: c.data.startswith("date"), state=AdminBookingState.date
)
async def process_date_selection(
    callback_query: types.CallbackQuery, state: FSMContext
):
    selected_date = callback_query.data.split(":")[1]
    await state.update_data(date=selected_date)
    await bot.send_message(
        callback_query.from_user.id,
        "Please select a time:",
        reply_markup=generate_time_keyboard(),
    )
    await AdminBookingState.time.set()


@dp.callback_query_handler(
    lambda c: c.data.startswith("time"), state=AdminBookingState.time
)
async def process_time_selection(
    callback_query: types.CallbackQuery, state: FSMContext
):
    selected_time = callback_query.data.split(":")[1]
    await state.update_data(time=selected_time)
    data = await state.get_data()
    cur.execute(
        "UPDATE bookings SET team_name = ?, date = ?, time = ? WHERE id = ?",
        (data["team_name"], data["date"], selected_time, data["booking_id"]),
    )
    conn.commit()
    await bot.send_message(
        callback_query.from_user.id, f"Booking with ID {data['booking_id']} updated."
    )
    await state.finish()


@dp.message_handler(
    lambda message: message.text == "View Statistics" and is_admin(message.from_user.id)
)
async def view_statistics(message: types.Message):
    cur.execute("SELECT COUNT(*) AS total_bookings FROM bookings")
    total_bookings = cur.fetchone()[0]
    await message.answer(f"Total bookings: {total_bookings}")


@dp.message_handler(
    lambda message: message.text == "Export Data" and is_admin(message.from_user.id)
)
async def export_data(message: types.Message):
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    cur.execute(
        "SELECT * FROM bookings WHERE date BETWEEN ? AND ?", (start_date, end_date)
    )
    recent_bookings = cur.fetchall()
    df = pd.DataFrame(recent_bookings, columns=["id", "team_name", "date", "time"])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"bookings_{timestamp}.xlsx"
    df.to_excel(filename, index=False)
    await message.answer_document(InputFile(filename))


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)