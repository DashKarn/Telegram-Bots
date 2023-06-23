import time
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.base import STATE_STOPPED, STATE_RUNNING, STATE_PAUSED
from bs4 import BeautifulSoup
import requests

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import  ReplyKeyboardMarkup, KeyboardButton

TOKEN = "6123350878:AAGS85GrsJXfNiT6mF36fs2Z4oGUXdhE0do"
MSG_HI = """Привет!
Я бот для уведомления об акции дня.
Каждый день в 12:00 тебе будет приходить название и фото выкройки дня со ссылкой. 
Если сайт будет недоступен, я уведомлю тебя и буду проверять его работу каждый час. 
Также ты в любой момент можешь запросить получение актуальной выкройки вызовом <b>/new</b>"""
MSG_HELP = """ 
Команды:
<b>/start</b>  -- возобновить уведомления
<b>/pause</b>  --  поставить на паузу уведомления
<b>/new</b>  -- получить выкройку дня
<b>/help</b>  -- помощь
"""
MSG_ERROR = "Извините, не удаётся получить доступ к сайту :( \
Я попробую обратиться через час, у меня есть 5 попыток."
MSG_PAUSE = "Автоматические уведомления приостановлены, чтобы возобновить, нажмите <b>/start</b>"
MSG_RESUME = "Автоматические уведомления восстановлены"
MSG_RUNNING = "Бот с уведомлениями уже запущен"

URL = 'https://patterneasy.com'
WAITING_FLAG = 0

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot=bot)
scheduler = AsyncIOScheduler()

kb_all = ReplyKeyboardMarkup(resize_keyboard=True)
kb_started = ReplyKeyboardMarkup(resize_keyboard=True)
kb_paused = ReplyKeyboardMarkup(resize_keyboard=True)
b0 = KeyboardButton(text="/start")
b1 = KeyboardButton(text="/help")
b2 = KeyboardButton(text="/pause")
b3 = KeyboardButton(text="/new")

kb_all.add(b0, b1, b2, b3)
kb_started.add(b1, b2, b3)
kb_paused.add(b0, b1, b3)


def get_page_info():
    empty = ('', '', '')
    pattern_url, pattern_info, pattern_image_url = empty
    try:
        page = requests.get(URL)
        page.raise_for_status()
    except Exception as e:
        return empty
    soup = BeautifulSoup(page.content, "html.parser")
    product_classes = soup.find_all('div', {'class':'product'})
    for p_class in product_classes:
        if p_class.find('img', attrs={'title':'Выкройка дня'}):
            target = p_class.find('div', {'class':'product__title'})
            pattern_info = target.a.text
            pattern_url = URL + target.a['href']
            break
    if not pattern_url or not pattern_info:
        return empty
    try:
        pattern_page = requests.get(pattern_url)
        pattern_page.raise_for_status()
    except Exception as e:
        return empty
    soup = BeautifulSoup(pattern_page.content, "html.parser")
    pattern_image_url = soup.find('img', {'data-id': '0'})['src']
    if not pattern_image_url:
        return empty
    return pattern_url, pattern_info, pattern_image_url


@dp.message_handler(commands=['help'])
async def help_handler(message: types.Message):
    await message.answer(MSG_HELP, parse_mode='HTML')

@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    if not scheduler.get_jobs():
        scheduler.add_job(new_handler, 'cron', args=[message], hour=12, minute=0, second=0, timezone='Europe/Minsk')
        scheduler.start()
        await message.answer(MSG_HI, parse_mode='HTML', reply_markup=kb_started)
    elif scheduler.state == STATE_PAUSED:
        scheduler.resume()
        await message.answer(MSG_RESUME, reply_markup=kb_started)
    elif scheduler.state == STATE_RUNNING:
        await message.answer(MSG_RUNNING)


@dp.message_handler(commands=["pause"])
async def pause_handler(message: types.Message):
    if scheduler.get_jobs():
        if scheduler.running:
            scheduler.pause()
    await message.answer(MSG_PAUSE, parse_mode='HTML', reply_markup=kb_paused)


@dp.message_handler(commands=["new"])
async def new_handler(message: types.Message):
    global WAITING_FLAG
    if WAITING_FLAG:
        return
    for i in range(5):
        pattern_url, pattern_info, pattern_image_url = get_page_info()
        pattern_caption = pattern_info + "\nСсылка " + pattern_url
        if pattern_url:
            await bot.send_photo(message.chat.id, pattern_image_url, pattern_caption)
            time.sleep(5)
            WAITING_FLAG = 0
            break
        else:
            await bot.send_message(message.chat.id, MSG_ERROR)
        time.sleep(60*60)

if __name__ == "__main__":
    executor.start_polling(dp)
