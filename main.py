#импорты для работы бота
import telebot
from telebot import types
import os
from time import sleep

#импорты для работы со скриптами
import argparse
import getpass
import sys
from pathlib import Path
import dnevnik2

#получение оценок
import datetime as dt
import json
from collections import defaultdict
from typing import Dict

import pip._vendor.pkg_resources as pkg_resources
from pip._vendor import tomli as toml

from dnevnik2 import Dnevnik2


bot = telebot.TeleBot("token")

getEmail = False
getPass = False
global userID

def keyboard1():
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("Да", callback_data="confirmlogin")
    markup.add(button1)
    return markup

def keyboard2():
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("Меню", callback_data="menu")
    button2 = types.InlineKeyboardButton("Запросить снова", callback_data="get_marks")
    markup.add(button1, button2)
    return markup

def menukb():
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("Запросить оценки", callback_data="get_marks")
    button2 = types.InlineKeyboardButton("Выйти из аккаунта", callback_data="logout")
    markup.add(button1)
    markup.add(button2)
    return markup

def logoutkb():
    markup = types.InlineKeyboardMarkup()
    button1 = types.InlineKeyboardButton("Да", callback_data="confirm_logout")
    button2 = types.InlineKeyboardButton("Нет", callback_data="menu")
    markup.add(button1)
    markup.add(button2)
    return markup

@bot.message_handler(commands=["start"])
def handle_command(message):
    global getEmail
    try:
        f = open(str(message.chat.id) + ".txt", 'r')
        bot.send_message(message.chat.id, f"Вы уже авторизованы!", reply_markup=keyboard2())
    except:
        bot.send_message(message.chat.id, "Привет! Чтобы узнать свои оценки, Вам нужно войти. Введите почту")
        getEmail = True   

@bot.message_handler(content_types=['text'])
def handle_text(message):
    global getEmail
    global getPass
    if getEmail == True:
        f = open(str(message.chat.id) + ".txt", 'a')
        f.write(message.text + "\n")
        f.close()
        getEmail = False
        getPass = True
        bot.send_message(message.chat.id, "Отлично, теперь введите пароль.")
    elif getPass == True:
        f = open(str(message.chat.id) + ".txt", 'a')
        f.write(message.text)
        f.close()
        getPass = False

        f = open(str(message.chat.id) + ".txt", 'r')
        lines = f.readlines()
        email = lines[0]
        password = lines[1]
        bot.send_message(message.chat.id, f"Почта: {email}\nПароль: {password}\nВсё верно?", reply_markup=keyboard1())
        f.close()
    else:
        bot.send_message(message.chat.id, "Неизвестная команда.")
    bot.delete_message(message.chat.id, message.message_id)  

@bot.callback_query_handler(func=lambda call: call.data == "confirmlogin")
def checkValid(call):
    global email
    global password
    #arg_parser = argparse.ArgumentParser()
    #arg_parser.add_argument('cookies_path')
    #args = arg_parser.parse_args()

    f = open(str(call.from_user.id) + ".txt", 'r')
    lines = f.readlines()
    email = lines[0]
    password = lines[1]

    f.close()

    cookies_path = Path(str(call.from_user.id) + ".json").expanduser()

    #email = input(f'Email for {dnevnik2.BASE_URL}: ')
    #password = input()#getpass.getpass()
    try:
        dnevnik = dnevnik2.Dnevnik2.make_from_login_by_email(email, password)
        dnevnik.save_cookies(cookies_path)

        bot.send_message(call.from_user.id, "Отлично! Теперь вы можете запросить Ваши оценки!", reply_markup=keyboard2())       
    except:
        bot.send_message(call.from_user.id, "Данные не верны! Попробуйте ещё раз, прописав /start заново.")
        file = str(call.from_user.id) + ".txt"
        os.remove(file)
    bot.delete_message(call.message.chat.id, call.message.message_id)  

def get_subject(item, subjects: Dict[str, str]) -> str:
    subject_id = str(item['subject_id'])
    return subjects.get(subject_id, item['subject_name'])


def to_date(text):
    return dt.datetime.strptime(text, '%d.%m.%Y').date()

@bot.callback_query_handler(func=lambda call: call.data == "menu")
def menu(call):
    bot.send_message(call.from_user.id, "Ты находишься в меню! Выбери действие", reply_markup=menukb())
    bot.delete_message(call.message.chat.id, call.message.message_id)  

@bot.callback_query_handler(func=lambda call: call.data == "logout")
def confirm_logout(call):
    bot.send_message(call.from_user.id, "Вы уверены, что хотите выйти?", reply_markup=logoutkb())
    bot.delete_message(call.message.chat.id, call.message.message_id)  

@bot.callback_query_handler(func=lambda call: call.data == "confirm_logout")
def logout(call):
    userID = str(call.from_user.id)
    os.remove(userID + ".txt")
    os.remove(userID + ".json")
    bot.send_message(call.from_user.id, "Пропишите /start, чтобы снова авторизоваться.")    
    bot.delete_message(call.message.chat.id, call.message.message_id)  

@bot.callback_query_handler(func=lambda call: call.data == "get_marks")
def getMarks(call):
    default_config_path = Path(pkg_resources.resource_filename('dnevnik2', 'app_config.toml')).resolve()
    default_output_dir = Path('.').resolve()
    arg_parser = argparse.ArgumentParser()
    #arg_parser.add_argument('cookies_path', type=Path)
    arg_parser.add_argument('--config_path', type=Path, default=default_config_path)
    arg_parser.add_argument('--output_dir', type=Path, default=default_output_dir)
    args = arg_parser.parse_args()

    #cookies_path: Path = (str(call.from_user.id) + ".json")
    cookies_path = Path(str(call.from_user.id) + ".json").expanduser()
    config_path: Path = args.config_path
    base_dir: Path = args.output_dir

    with config_path.open('rb') as f1:
        config = toml.load(f1)

    dnevnik = Dnevnik2.make_from_cookies_file(cookies_path)

    data = dnevnik.fetch_marks_for_current_quarter()

    #with (base_dir / 'last_res.txt').open('w', encoding='utf-8') as f1:
    #    print(json.dumps(data, ensure_ascii=False, indent=2), file=f1)

    out_lines = []
    grouped = defaultdict(list)
    for item in sorted(data['data']['items'], key=lambda x: (to_date(x['date']), x['estimate_value_name'])):
        s_name = item['subject_name'] = get_subject(item, config['subjects'])
        mark = item['estimate_value_name']
        if mark.isdigit():
            grouped[s_name].append(int(mark))
        comment = ('# ' + item['estimate_comment']) if item['estimate_comment'] else ''
        out_lines.append((
            to_date(item['date']),
            "{subject_name:25s} {estimate_value_code:5s} {estimate_value_name:9s} {estimate_type_name:20s}".format(
                **item),
            comment
        ))

    if not out_lines:
        exit(1)

    with (base_dir / f'marks.{call.from_user.id}.txt').open('a', encoding='utf-8') as f1:
        #for date, mark, comment in sorted(out_lines):
        #    print(f'{date}  {mark} {comment}', file=f1)

        #f1.write('\n\n')
        for s_name in sorted(grouped):
            avg = sum(grouped[s_name]) / len(grouped[s_name])
            s_marks = ', '.join(str(mark) for mark in grouped[s_name])
            print(f'{s_name} : \n{s_marks}  -  {avg:0.2f}\n', file=f1)

    d = dt.datetime.now()

    with (base_dir / f'marks.{call.from_user.id}.txt').open('a', encoding='utf-8') as f1:
        f1.write("Дата: " + str(d.strftime('%d/%m/%Y %H:%M:%S')))

    f1.close()

    with open("marks." + str(call.from_user.id) + ".txt", "rb") as f:
        contents = f.read().decode("UTF-8")
        bot.send_message(call.from_user.id, contents, reply_markup=keyboard2())
        bot.delete_message(call.message.chat.id, call.message.message_id)  

    os.remove("marks." + str(call.from_user.id) + ".txt")
bot.polling()
