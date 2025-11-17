from flask import Flask
from flask import request
from flask import jsonify
from flask_sslify import SSLify
from sqlite3 import Error
from datetime import datetime
import sqlite3
import requests
import json
import re
import os
import csv
import random

import Settings
import Mint_calendar



# ночные сообщения лучше сделать silent

app = Flask(__name__)
sslify = SSLify(app)

token = Settings.tg_token
URL = 'https://api.telegram.org/bot7726642478:'+ token

text = ', привет! Добро пожаловать в бот Дубровки!'
menu_button = '🔙 Меню'
months_ru = {'January': 'января','February': 'февраля','March': 'марта','April': 'апреля','May': 'мая','June': 'июня','July': 'июля','August': 'августа','September': 'сентября','October': 'октября','November': 'ноября','December': 'декабря'}
start_buttons_keyboard = json.dumps({'keyboard': [["🗓 В ближайший месяц"],["Дубровка", "Мята"]], 'one_time_keyboard': True, 'resize_keyboard': True})

# Глобальные переменные для хранения последних постов
dubrovka_last_post = None
mint_last_post = None


def send_start_message(chat_id, first_name, first_connection):
    url = URL + '/sendMessage'
    keyboard = start_buttons_keyboard        

    if first_connection == 'start':
        text = first_name + ', привет! Я бот Дубровки. Могу присылать тебе уведомления о дискотеках'
    elif first_connection == 'menu':
        text = first_name + random.choice(Settings.recommendations)
    answer = {'chat_id': chat_id, 'text': text, 'reply_markup': keyboard}
    r = requests.post(url, json=answer)
    return r.json()


def send_anonse_message(chat_id):
    url = URL + '/sendMessage'
    keyboard = start_buttons_keyboard
    # Получаем все события
    sorted_disco = Mint_calendar.sort_disco_dates()
    formatted_events = []
    current_date = datetime.now().date()

    # Собираем события в отдельные списки для каждого места
    dubrovka_events = []
    mint_events = []
    
    # Собираем события Дубровки
    for event in sorted_disco.get('Dubrovka', []):
        date_obj = datetime.strptime(event['date'], '%Y-%m-%d')
        event_date = date_obj.date()
        if event_date >= current_date:
            dubrovka_events.append({
                'date_obj': date_obj,
                'place': "Дубровка",
                'event': event['description']
            })
            if len(dubrovka_events) == 4:
                break
            
    # Собираем события Мяты
    for event in sorted_disco.get('Mint', []):
        date_obj = datetime.strptime(event['date'], '%Y-%m-%d')
        event_date = date_obj.date()
        if event_date >= current_date:
            mint_events.append({
                'date_obj': date_obj,
                'place': "Мята",
                'event': event['description']
            })
            if len(mint_events) == 4:
                break
    
    # Объединяем и сортируем все события по дате
    all_events = dubrovka_events + mint_events
    all_events.sort(key=lambda x: x['date_obj'])
    
    # Форматируем события
    for event in all_events:
        day = event['date_obj'].strftime('%d')
        month_eng = event['date_obj'].strftime('%B')
        month_ru = months_ru[month_eng]
        date_str = f"{day} {month_ru}"

        if event['event']:
            event_str = f"{date_str} - {event['place']}: {event['event']}"
        else:
            event_str = f"{date_str} - {event['place']}"
        formatted_events.append(event_str)
    
    if formatted_events:
        text = "В ближайшее время у нас:\n" + "\n".join(formatted_events)
    else:
        text = "На данный момент нет запланированных событий"
        
    answer = {'chat_id': chat_id, 'text': text, 'reply_markup': keyboard}
    r = requests.post(url, json=answer)
    return r.json()


def send_event_message(chat_id, group_id, event):
    url = URL + '/sendMessage'
    events = Mint_calendar.show_events_by_type(event)
    formatted_events = []
    if events and len(events) > 0:
        if event in ['league', 'multidance', 'junior', 'tdd-bg', 'tdd-rs', 'porosl']:
            # Специальное форматирование для всех типов регулярных событий
            first_event = events[0]
            date_obj = datetime.strptime(first_event['date'], '%Y-%m-%d')
            day = date_obj.strftime('%d')
            month_eng = date_obj.strftime('%B')
            month_ru = months_ru[month_eng]
            
            if event == 'league':
                text = f"Следующая Лига Дубровки пройдет {day} {month_ru}"
                next_dates_intro = "\nПотом насладиться шоу можно будет"
            elif event == 'multidance':
                text = f"Следующий Мультиденс пройдет {day} {month_ru}"
                next_dates_intro = "\nПосле этого шаркаем синкопы"
            elif event == 'junior':
                text = f"Следующая Младшая лига пройдет {day} {month_ru}"
                next_dates_intro = "\nПосле этого танцоры уровня Main порадуют нас своим пением"
            elif event == 'tdd-bg' :
                text = f"Следующий мини-турнир ТДД для танцоров уровня Beginner пройдет {day} {month_ru}"
                next_dates_intro = "\nПосле этого встретимся"
            elif event == 'tdd-rs' :
                text = f"Следующий мини-турнир ТДД Rising Star пройдет {day} {month_ru}"
                next_dates_intro = "\nПосле этого встретимся"
            elif event == 'porosl' :
                text = f"Следующая Поросль Дубровки планируется {day} {month_ru}"
            else:
                text = f"Что-то интересное будет {day} {month_ru}"
            
            # Добавляем информацию о последующих датах, если они есть
            if len(events) > 1:
                next_dates = []
                for event in events[1:]:
                    date_obj = datetime.strptime(event['date'], '%Y-%m-%d')
                    day = date_obj.strftime('%d')
                    month_eng = date_obj.strftime('%B')
                    month_ru = months_ru[month_eng]
                    next_dates.append(f"{day} {month_ru}")
                
                if len(next_dates) == 1:
                    text += f"{next_dates_intro} {next_dates[0]}"
                else:
                    *first_dates, last_date = next_dates
                    dates_str = ", ".join(first_dates)
                    text += f"{next_dates_intro} {dates_str} и {last_date}"
        else:
            # Стандартное форматирование для остальных типов событий
            for event in events:
                date_obj = datetime.strptime(event['date'], '%Y-%m-%d')
                day = date_obj.strftime('%d')
                month_eng = date_obj.strftime('%B')
                month_ru = months_ru[month_eng]
                date_str = f"{day} {month_ru}"

                place_name = "Дубровка" if event['place'] == 'Dubrovka' else "Мята"
                event_str = f"{date_str} - {place_name}: {event['event']}"
                formatted_events.append(event_str)
            text = "Ближайшие события:\n" + "\n".join(formatted_events)
    else:
        text = "На данный момент нет запланированных событий"

    keyboard = send_menu_buttons(chat_id, group_id)
    answer = {'chat_id': chat_id, 'text': text, 'reply_markup': keyboard}
    r = requests.post(url, json=answer)
    return r.json()

def send_menu_message(chat_id, group_id):
    menu_message = 'Узнать больше о дискотеке и ближайших мероприятиях, а так же изменить подписку:'
    url = URL+ '/sendMessage'
    keyboard = send_menu_buttons(chat_id, group_id)
    answer = {'chat_id': chat_id, 'text': menu_message, 'reply_markup': keyboard}
    r = requests.post(url, json=answer)
    print(r)
    return r.json()


def send_menu_buttons(chat_id, group_id):
    group_name = 'Dubrovka' if group_id == '-7959989' else 'Mint'
    subscriptions = get_user_subscriptions(chat_id)
    if group_name == 'Dubrovka':
        info_button = '🐿 О дискотеке'
        address_button = 'Адрес 🦊'
        league_button = '🏆 Лига Дубровки'
        another_button = 'Мультиденс 🙏'
        another_button_2 = 'ТДД Bg ✨'
        if not subscriptions[group_name]:
            subscribe_button = 'Подписаться на новости Дубровки'
            # status_notification = '❌ Сейчас подписка Дубровки отменена'
        else:
            subscribe_button = 'Отписаться от новостей Дубровки'
            # status_notification = '✅ Сейчас подписка активна'
    else:
        info_button = '🌿 О дискотеке'
        address_button = 'Адрес 🚀'
        league_button = '⭐️ Младшая лига'
        another_button = 'ТДД Rs ✨'
        another_button_2 = ''
        if not subscriptions[group_name]:
            subscribe_button = 'Подписаться на новости Мяты'
            # status_notification = '❌ Сейчас подписка Мяты отменена'
        else:
            subscribe_button = 'Отписаться от новостей Мяты'
            # status_notification = '✅ Сейчас подписка Мяты активна' 
    keyboard = json.dumps({'keyboard': [[menu_button],[league_button, another_button, another_button_2],[info_button, address_button],[subscribe_button]], 'one_time_keyboard': True, 'resize_keyboard': True})
    return keyboard

def send_address_message(chat_id, group_id):
    group_name = 'Dubrovka' if group_id == '-7959989' else 'Mint'
    url = URL+ '/sendPhoto'
    if group_name == 'Dubrovka':
        photo_address = 'https://sun9-3.userapi.com/impg/p9Ov3SQVAZLG-i6xTUTtUWCfy3V5t20-P_Ttag/W3EEr-Et8Uo.jpg?size=1298x917&quality=95&sign=1db6e4ef1241e9965801c7603967328a&type=album'
        text_address = 'Старокирочный переулок дом 2, третий этаж.\n \n👣 КАК ПРОЙТИ ОТ МЕТРО БАУМАНСКАЯ.\n⏱️ Дорога от метро занимает 7-10 минут, ехать удобнее в 4 вагоне из центра.\n📍 Выходя из метро пройдите направо, в сторону остановки и поверните налево. \nПройдите по ул. Бауманская до пересечения со Старокирочным переулком – это первый перекресток со светофором. \nПереходите улицу и сразу поворачиваете налево. Продолжайте движение вдоль розового трехэтажного здания, пока не увидите справа коричневые ворота и дверь. \nЗа дверью проходная, пройдите через турникеты и сворните налево, чтобы выйти во двор. Поворачивайте направо и продлжайте движение до 5 этажного здания с зелеными дверьми, входите. \nМы находимся на третьем этаже, рыжая дверь с левой стороны. \n \n ❗️ ВНИМАНИЕ ❗️ \nВ здании пропускной режим. \nПри себе нужно иметь паспорт или загранпаспорт! \nНа проходной вам оформят временный пропуск, его нужно будет сдать на выходе. \nЧтобы получить постоянный пропуск — напишите в личные сообщения организаторам.'
    else:
        photo_address = 'https://sun9-47.userapi.com/impg/gvLi2vj7EKDPNHM8TXZ_Qx3fa8qhJ55UzIL9QQ/ROUjXRoixng.jpg?size=769x977&quality=95&sign=1b260b8410e9cf48072ce5b8e1bfb777&type=album'
        text_address = 'Ленинский проспект 45, строение 1, третий этаж.\n \n👣 КАК ПРОЙТИ ОТ МЕТРО ЛЕНИНСКИЙ ПРОСПЕКТ.\n⏱️ Дорога от метро занимает примерно 7-10 минут, eхать удобнее в первом вагоне из центра \n📍 Выход №1 из метро Ленинский проспект на ул. Вавилова. \nВыходя из метро поворачиваем направо, проходим «Магнолию» и еще раз поворачиваем направо.\nПо Вавилова двигаемся прямо до большого перекрестка. \nПереходим на светофоре проспект 60-летия Октября в сторону здания GT Drive, и затем идем в сторону бульвара Академика Зелинского (в направлении к многоэтажному офисному зданию с голубой подсветкой). \nВам нужно обойти офисное здание с правой стороны и завернуть за него. \nСлева вы увидите автомойку, рядом с ней четырехэтажное кирпичное здание за черным забором и светящуюся вывеску «Студия танцев IVARA». \nЗаходите в калитку, обходите здание слева и входите в дальний подъезд. Мы находимся на третьем этаже. \n \n ПАРКОВКА \n 🚗 Во дворах и близлежащих улочках парковка бесплатная, обращайте внимание на знаки.'
    keyboard = send_menu_buttons(chat_id, group_id)
    answer = {'chat_id': chat_id, 'photo': photo_address, 'caption': text_address, 'parse_mode': 'HTML', 'reply_markup': keyboard}
    r = requests.post(url, json=answer)
    # print(r)
    return r.json()


def send_info_message(chat_id, group_id):
    try:
        group_name = 'Dubrovka' if group_id == '-7959989' else 'Mint'
        url = URL + '/sendPhoto'
        if group_name == 'Dubrovka':
            photo_info ='https://sun9-6.userapi.com/s/v1/ig2/EWOZRTFaIlOHIrdGVPB2mWbt6T-IbPA5NDLjlMO6jD1y6_J_FgiBAqVebm-ChUqH-qzpHf0kxiE6fIl-6_QHHwmj.jpg?quality=95&as=32x32,48x48,72x72,108x108,160x160,240x240,360x360,480x480,540x540,640x640,720x720,1080x1080,1280x1280,1440x1440,2480x2480&from=bu&cs=2480x0'
            text_info = 'Еженедельная субботняя хастл-вечеринка\n\nДЛЯ ВАС ВСЕГДА:\n🟠 Большой танцевальный зал\n🔵 Малый зал с микс-подборкой\n\nА ТАК ЖЕ:\n🔓 Камера хранения (пожалуйста, не оставляйте ценные вещи в раздевалке или танцевальном зале)\n🥤 Куллер (настоятельно просим не проносить напитки в открытой таре в зону танцпола)\n🍊 Освежающие фрукты\n🫖 Чай с печеньками\n👕 Раздельные раздевалки\n\n👟 Сменная обувь обязательна, мы ценим ваш комфорт и хотим долго сохранять как вашу танцевальную обувь, так и паркет в хорошем состоянии\n\n💵 Стоимость: 700₽ \nДля постоянных посетителей предлагаем абонемент:\n4 посещения — 2600₽ (срок действия 4 месяца)\n\n‼️ Напоминаем, что для проходной нужен оригинал паспорта (можно загранпаспорт), для согласования прохода иностранцев напишите в личку организаторам.'
        else:
            photo_info = 'https://sun9-14.userapi.com/impg/dYPXpJ9NUARuIoTTaszkT8Ocz27LKFduPcaMZw/Ct0EoQlKc84.jpg?size=1080x1080&quality=95&sign=114011a7002ca33bb94b51db40e781de&type=album'
            text_info = 'Еженедельная воскресная хастл-вечеринка для танцоров всех уровней\n\nДЛЯ ВАС ВСЕГДА:\n🟢 Зал для начинающих танцоров, где звучат треки с четким и понятным ритмом\n🔴 Зал с релакс-треками, для тех кто любит медленные душевные композиции\n🟠 Большой танцевальный холл с MIX-подборкой\n🟣 Сиреневый зал — еще один миксовый зал или выручай-комната в дни дополнительных активностей\n\nА ТАК ЖЕ:\n🔓 Камера хранения (пожалуйста, не оставляйте ценные вещи в раздевалке или танцевальном зале)\n🥤 Куллер (настоятельно просим не проносить напитки в открытой таре в зону танцпола)\n🍊 Освежающие фрукты\n🫖 Чай с печеньками\n🚿 Комфортные раздельные раздевалки с душевыми\n\n👟 Сменная обувь обязательна, мы ценим ваш комфорт и хотим долго сохранять вашу танцевальную обувь и наш пол в хорошем состоянии\n\n💵 Стоимость: 700₽ \nДля постоянных посетителей предлагаем абонементы:\n3 посещения — 2000₽\n5 посещений — 3200₽\nАбонементы бессрочные, в случае потери не восстанавливаем, берегите их.'
        keyboard = send_menu_buttons(chat_id, group_id)
        answer = {'chat_id': chat_id, 'photo': photo_info, 'caption': text_info, 'parse_mode': 'HTML', 'reply_markup': keyboard}
        print(f"Отправка send_info_message для {group_name}, chat_id: {chat_id}")
        print(f"URL фото: {photo_info[:100]}...")  # Первые 100 символов URL
        r = requests.post(url, json=answer, timeout=30)
        print(f"Ответ от Telegram API: {r.status_code}, {r.text[:200]}")  # Первые 200 символов ответа
        if r.status_code == 200:
            return r.json()
        else:
            print(f"Ошибка от Telegram API: статус {r.status_code}, ответ: {r.text}")
            return None
    except Exception as e:
        print(f"Ошибка в send_info_message: {e}")
        import traceback
        traceback.print_exc()
        return None







def load_anonse_from_csv(group_id):
    """
    Загружает анонс для указанной группы из CSV файла.
    Возвращает post_data (словарь) или None, если анонс не найден.
    
    Формат данных для process_vk_post:
    post_data должен быть словарем с полями:
    - text: str - текст поста
    - date: int - timestamp даты поста
    - attachments: list - список вложений, где каждое вложение это словарь с полем 'type'
      и соответствующими полями в зависимости от типа (photo, video, audio, link)
    """
    filename = 'anonces.csv'
    
    if not os.path.exists(filename):
        return None
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3 and row[0] == group_id:
                    # Нашли запись для этой группы, парсим JSON из третьего столбца
                    try:
                        data = json.loads(row[2])
                        post_data = data.get('post_data')
                        if post_data:
                            # Проверяем наличие обязательных полей для process_vk_post
                            if isinstance(post_data, dict) and 'text' in post_data and 'date' in post_data:
                                return post_data
                            else:
                                print(f"Данные в CSV для {group_id} не соответствуют формату для process_vk_post")
                                print(f"Ожидается словарь с полями: text, date, attachments (опционально)")
                                return None
                    except json.JSONDecodeError as e:
                        print(f"Ошибка при парсинге JSON для {group_id}: {e}")
                        return None
        return None
    except Exception as e:
        print(f"Ошибка при чтении файла {filename}: {e}")
        return None


def process_vk_post(post_object):
    """
    Обрабатывает пост из VK webhook и возвращает данные в формате:
    (tg_post_text, post_photos, post_video, video_cover, post_audio, post_link, post_time)
    """
    post_text = post_object.get('text', '')
    tg_post_text = re.sub(r'\[([^|]+)\|(.*?)\]', r'<a href="https://vk.com/\1">\2</a>', post_text)
    post_time = post_object.get('date', 0)
    attachments = post_object.get('attachments', [])
    
    post_photos = 'empty'
    post_video = 'empty'
    video_cover = 'empty'
    post_audio = 'empty'
    post_link = 'empty'
    
    if not attachments:
        return tg_post_text, 'empty', 'empty', 'empty', 'empty', 'empty', post_time
    
    # Проверяем первое вложение для определения типа
    attachment_type = attachments[0].get('type')
    print(f'Тип вложения: {attachment_type}')
    
    if attachment_type == 'photo':
        try:
            post_photos = []
            for idx, attachment in enumerate(attachments):
                if attachment.get('type') == 'photo':
                    # Ищем максимальное качество фото
                    photo = attachment['photo']
                    photo_url = None
                    
                    # Сначала пробуем orig_photo (как в оригинальном VK_posts)
                    if 'orig_photo' in photo and 'url' in photo['orig_photo']:
                        photo_url = photo['orig_photo']['url']
                    else:
                        # Пробуем найти максимальное разрешение по полям
                        for size_key in ['photo_2560', 'photo_1280', 'photo_807', 'photo_604', 'photo_130']:
                            if size_key in photo:
                                photo_url = photo[size_key]
                                break
                        # Если не нашли, пробуем массив sizes
                        if not photo_url and 'sizes' in photo:
                            sizes = photo['sizes']
                            if sizes:
                                photo_url = max(sizes, key=lambda x: x.get('width', 0) * x.get('height', 0)).get('url')
                    
                    if photo_url:
                        media_item = {
                            'type': 'photo',
                            'media': photo_url,
                            'caption': tg_post_text if idx == 0 else '',
                            'parse_mode': 'HTML' if idx == 0 else ''
                        }
                        post_photos.append(media_item)
            
            if not post_photos:
                post_photos = 'empty'
        except Exception as e:
            print(f'Ошибка при обработке фото: {e}')
            post_photos = 'empty'
    
    elif attachment_type == 'video':
        try:
            video = attachments[0]['video']
            if 'image' in video and len(video['image']) > 0:
                video_cover = video['image'][-1].get('url', 'empty')
            video_id = video.get('id')
            video_owner_id = video.get('owner_id')
            if video_id and video_owner_id:
                post_video = f'https://vk.com/video{video_owner_id}_{video_id}'
        except Exception as e:
            print(f'Ошибка при обработке видео: {e}')
            post_video = 'empty'
            video_cover = 'empty'
    
    elif attachment_type == 'audio':
        try:
            all_tracks = []
            for attachment in attachments:
                if attachment.get('type') == 'audio':
                    audio = attachment['audio']
                    track = f"{audio.get('artist', '')} - {audio.get('title', '')}"
                    track_url = audio.get('url', '')
                    if track_url:
                        track_html = f'<a href="{track_url}">{track}</a>'
                        all_tracks.append(track_html)
            if all_tracks:
                post_audio = '\n'.join(all_tracks)
        except Exception as e:
            print(f'Ошибка при обработке аудио: {e}')
            post_audio = 'empty'
    
    elif attachment_type == 'link':
        try:
            post_link = attachments[0]['link'].get('url', 'empty')
        except Exception as e:
            print(f'Ошибка при обработке ссылки: {e}')
            post_link = 'empty'
    
    return tg_post_text, post_photos, post_video, video_cover, post_audio, post_link, post_time


def send_message(chat_id, group_id):
    """
    Отправляет сообщение пользователю.
    Сначала пытается получить анонс из CSV, если нет - использует last_post.
    """
    if group_id == '-7959989':
        group_name = 'Dubrovka'
    elif group_id == '-127965281':
        group_name = 'Mint'
    else: 
        group_name = None
    
    global dubrovka_last_post, mint_last_post
    
    # Получаем данные из CSV
    anonse_data = load_anonse_from_csv(group_id)
    
    if anonse_data:
        # Если данные есть в CSV для этой группы, обрабатываем и отправляем
        tg_post_text, post_photos, post_video, video_cover, post_audio, post_link, post_time = process_vk_post(anonse_data)
        return send_post_data(chat_id, tg_post_text, post_photos, post_video, video_cover, post_audio, post_link)
    else:
        # Если данных нет в CSV, используем last_post
        if group_name == 'Dubrovka' and dubrovka_last_post:
            tg_post_text, post_photos, post_video, video_cover, post_audio, post_link, post_time = dubrovka_last_post
            print(dubrovka_last_post)
            return send_post_data(chat_id, tg_post_text, post_photos, post_video, video_cover, post_audio, post_link)
        elif group_name == 'Mint' and mint_last_post:
            tg_post_text, post_photos, post_video, video_cover, post_audio, post_link, post_time = mint_last_post
            return send_post_data(chat_id, tg_post_text, post_photos, post_video, video_cover, post_audio, post_link)
        else:
            # Если ничего нет
            print('Поста пока нет')
            # url = URL + '/sendMessage'
            # message = f"Анонс для группы {group_name.title()} пока не установлен"
            # answer = {'chat_id': chat_id, 'text': message}
            # return requests.post(url, json=answer).json()



def handle_vk_webhook(vk_data):
    """Обработчик VK webhook"""
    event_type = vk_data.get('type')
    group_id = vk_data.get('group_id')
    
    print(f"VK webhook: type={event_type}, group_id={group_id}")
    
    if group_id == 7959989:  # Дубровка
        if event_type == 'confirmation':
            return Settings.Dubrovka_accept  # Код подтверждения для Дубровки
        elif event_type == 'wall_post_new':
            print('Новый пост в Дубровке:', vk_data)
            notify_subscribers('Dubrovka', vk_data)
            return 'ok'
    
    elif group_id == 127965281:  # Мята
        if event_type == 'confirmation':
            return Settings.Mint_accept  # Код подтверждения для Мяты
        elif event_type == 'wall_post_new':
            print('Новый пост в Мяте:', vk_data)

            
            # Отправляем уведомления подписчикам Мяты
            notify_subscribers('Mint', vk_data)
            return 'ok'
    
    return 'ok'


def notify_subscribers(group_name, vk_data):
    """Отправляет уведомления подписчикам о новом посте"""
    global dubrovka_last_post, mint_last_post
    
    try:
        # Получаем всех подписчиков группы
        conn = create_connection()
        if conn is not None:
            c = conn.cursor()
            c.execute(f'SELECT chat_id FROM subscriptions WHERE {group_name} = 1')
            subscribers = c.fetchall()
            
            print(f"Отправляем уведомления {len(subscribers)} подписчикам группы {group_name}")
            
            # Обрабатываем пост из webhook
            post_object = vk_data.get('object', {})
            tg_post_text, post_photos, post_video, video_cover, post_audio, post_link, post_time = process_vk_post(post_object)
            
            # Обновляем last_post для соответствующей группы
            if group_name == 'Dubrovka':
                dubrovka_last_post = (tg_post_text, post_photos, post_video, video_cover, post_audio, post_link, post_time)
            elif group_name == 'Mint':
                mint_last_post = (tg_post_text, post_photos, post_video, video_cover, post_audio, post_link, post_time)
            
            # Отправляем уведомление каждому подписчику
            for (chat_id,) in subscribers:
                try:
                    send_post_data(chat_id, tg_post_text, post_photos, post_video, video_cover, post_audio, post_link)
                except Exception as e:
                    print(f"Ошибка при отправке уведомления пользователю {chat_id}: {e}")
            
            conn.close()
    except Exception as e:
        print(f"Ошибка при отправке уведомлений: {e}")


def send_post_data(chat_id, tg_post_text, post_photos, post_video, video_cover, post_audio, post_link):
    """Отправляет пост с данными в Telegram"""
    keyboard = start_buttons_keyboard
    
    if video_cover != 'empty':
        url = URL + '/sendPhoto'
        answer = {
            'chat_id': chat_id, 
            'photo': video_cover, 
            'caption': f"{post_video}\n{tg_post_text}", 
            'parse_mode': 'HTML',
            'reply_markup': keyboard
        }
    elif post_photos != 'empty':
        url = URL + '/sendMediaGroup'
        answer = {
            'chat_id': chat_id, 
            'media': post_photos,
            'reply_markup': keyboard
        }
    elif post_link != 'empty':
        url = URL + '/sendMessage'
        caption = tg_post_text
        answer = {
            'chat_id': chat_id, 
            'text': caption, 
            'parse_mode': 'HTML',
            'reply_markup': keyboard
        }
    elif post_audio != 'empty':
        url = URL + '/sendMessage'
        audio_message = f"{tg_post_text}\n{post_audio}"
        answer = {
            'chat_id': chat_id, 
            'text': audio_message, 
            'parse_mode': 'HTML',
            'reply_markup': keyboard
        }
    else:
        url = URL + '/sendMessage'
        answer = {
            'chat_id': chat_id, 
            'text': tg_post_text, 
            'parse_mode': 'HTML',
            'reply_markup': keyboard
        }
    
    r = requests.post(url, json=answer)
    return r.json()


@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        r = request.get_json()
        print("Получено обновление:", r)  # Добавить перед обработкой
        try:
            # Проверяем, это VK webhook или Telegram webhook
            if 'type' in r and 'group_id' in r:
                # Это VK webhook
                return handle_vk_webhook(r)
            elif 'message' in r:
                chat_id = r['message']['chat']['id']
                message = r['message'].get('text', '')
                first_name = r['message']['chat']['first_name']
                
                # Отладочный вывод для проверки сообщений
                print(f"Получено сообщение: '{message}' (длина: {len(message) if message else 0})")
                if message:
                    print(f"Байты сообщения: {message.encode('utf-8')[:50]}...")
                    print(f"Сравнение с '🐿 О дискотеке': {message == '🐿 О дискотеке'}")
                    print(f"Сравнение с '🌿 О дискотеке': {message == '🌿 О дискотеке'}")
                
                if '/start' in message:
                    send_start_message(chat_id, first_name, 'start')
                elif message == '🔙 Меню':
                    send_start_message(chat_id, first_name, 'menu')
                elif message == '🗓 В ближайший месяц':
                    send_anonse_message(chat_id)
                elif message == 'Дубровка':
                    send_menu_message(chat_id, '-7959989')
                elif message == 'Мята':
                    send_menu_message(chat_id, '-127965281')
                elif message == "Управление подписками":
                    send_subscription_status(chat_id)
                elif message == "Подписаться на новости Дубровки":
                    manage_subscription(chat_id, 'Dubrovka', True)
                    send_subscription_status(chat_id)
                    # Отправляем закрепленный пост (анонс) при подписке
                    send_message(chat_id, '-7959989')
                elif message == "Отписаться от новостей Дубровки":
                    manage_subscription(chat_id, 'Dubrovka', False)
                    send_subscription_status(chat_id)
                elif message == "Подписаться на новости Мяты":
                    manage_subscription(chat_id, 'Mint', True)
                    send_subscription_status(chat_id)
                    # Отправляем закрепленный пост (анонс) при подписке
                    send_message(chat_id, '-127965281')
                elif message == "Отписаться от новостей Мяты":
                    manage_subscription(chat_id, 'Mint', False)
                    send_subscription_status(chat_id)
                elif message == "Адрес 🦊":
                    send_address_message(chat_id, '-7959989')
                elif message == "Адрес 🚀":
                    send_address_message(chat_id, '-127965281')
                elif message == "🐿 О дискотеке":
                    print("Обработка: 🐿 О дискотеке")
                    try:
                        result = send_info_message(chat_id, '-7959989')
                        print(f"Результат send_info_message: {result}")
                    except Exception as e:
                        print(f"Ошибка в send_info_message для Дубровки: {e}")
                        import traceback
                        traceback.print_exc()
                elif message == "🌿 О дискотеке":
                    print("Обработка: 🌿 О дискотеке")
                    try:
                        result = send_info_message(chat_id, '-127965281')
                        print(f"Результат send_info_message: {result}")
                    except Exception as e:
                        print(f"Ошибка в send_info_message для Мяты: {e}")
                        import traceback
                        traceback.print_exc()
                elif message == "🏆 Лига Дубровки":
                    send_event_message(chat_id, '-7959989', 'league')
                elif message == "⭐️ Младшая лига":
                    send_event_message(chat_id, '-127965281', 'junior')
                elif message == "Мультиденс 🙏":
                    send_event_message(chat_id, '-7959989', 'multidance')
                elif message == "ТДД Bg ✨":
                    send_event_message(chat_id, '-7959989', 'tdd-bg')
                elif message == "ТДД Rs ✨":
                    send_event_message(chat_id, '-127965281', 'tdd-rs')
                else:
                    print(f"Неизвестное сообщение, отправляем меню. Сообщение: '{message}'")
                    send_start_message(chat_id, first_name, 'menu')

                # write_json(r)
                return jsonify(r)
            elif 'callback_query' in r:
                chat_id = r['callback_query']['message']['chat']['id']
                # Обработка callback-запросов если они есть
            else:
                # Пропускаем другие типы обновлений
                return 'ok'
        except Exception as e:
            print(f"Ошибка при обработке обновления: {e}")
            import traceback
            traceback.print_exc()
            # Возвращаем 'ok' чтобы Telegram не повторял запрос
            return 'ok'
    return '<h1>Mind Disco Bot welcomes you!</h1>'




def main():
    pass


def create_connection():
    """Создает подключение к БД"""
    try:
        conn = sqlite3.connect('subscriptions.db')
        return conn
    except Error as e:
        print(f"Ошибка при подключении к БД: {e}")
        return None

def init_db():
    """Инициализация БД и создание таблицы, если она не существует"""
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            # Добавим проверку существования таблицы
            c.execute('''
                CREATE TABLE IF NOT EXISTS subscriptions
                (chat_id INTEGER PRIMARY KEY,
                 Dubrovka BOOLEAN NOT NULL DEFAULT 1,
                 Mint BOOLEAN NOT NULL DEFAULT 1)
            ''')
            conn.commit()
            print("База данных успешно инициализирована")
        except Error as e:
            print(f"Ошибка при создании таблицы: {e}")
        finally:
            conn.close()
    else:
        print("Не удалось создать соединение с базой данных")

def manage_subscription(chat_id, group_name, enable=True):
    """
    Управляет подписками пользователя на группы
    group_name: 'Dubrovka' или 'Mint'
    enable: True для включения, False для отключения подписки
    """
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            # Проверяем, существует ли запись для данного chat_id
            c.execute('SELECT * FROM subscriptions WHERE chat_id = ?', (chat_id,))
            result = c.fetchone()
            
            if result is None:
                # Если записи нет, создаем новую с дефолтными значениями
                c.execute('INSERT INTO subscriptions (chat_id, Dubrovka, Mint) VALUES (?, 1, 1)',
                         (chat_id,))
            
            # Обновляем значение подписки
            c.execute(f'UPDATE subscriptions SET {group_name} = ? WHERE chat_id = ?',
                     (1 if enable else 0, chat_id))
            
            conn.commit()
            
            # Получаем обновленные данные
            c.execute('SELECT Dubrovka, Mint FROM subscriptions WHERE chat_id = ?', (chat_id,))
            Dubrovka, Mint = c.fetchone()
            return {'dubrovka': bool(Dubrovka), 'Mint': bool(Mint)}
            
        except Error as e:
            print(f"Ошибка при работе с БД: {e}")
            return None
        finally:
            conn.close()

def get_user_subscriptions(chat_id):
    """Получает текущие подписки пользователя"""
    conn = create_connection()
    if conn is not None:
        try:
            c = conn.cursor()
            # Добавим больше логирования
            print(f"Проверяем подписки для chat_id: {chat_id}")
            
            c.execute('SELECT Dubrovka, Mint FROM subscriptions WHERE chat_id = ?', (chat_id,))
            result = c.fetchone()
            
            if result is None:
                print(f"Создаем новую запись для chat_id: {chat_id}")
                # Если записи нет, создаем новую с дефолтными значениями
                c.execute('INSERT INTO subscriptions (chat_id, Dubrovka, Mint) VALUES (?, 1, 1)',
                         (chat_id,))
                conn.commit()
                return {'Dubrovka': True, 'Mint': True}
            
            # print(f"Найдены подписки: Dubrovka={bool(result[0])}, Mint={bool(result[1])}")
            return {'Dubrovka': bool(result[0]), 'Mint': bool(result[1])}
            
        except Error as e:
            print(f"Ошибка при получении подписок: {e}")
            # В случае ошибки возвращаем дефолтные значения
            return {'Dubrovka': True, 'Mint': True}
        finally:
            conn.close()
    else:
        print("Не удалось подключиться к БД, возвращаем дефолтные значения")
        return {'Dubrovka': True, 'Mint': True}

def send_subscription_status(chat_id):
    url = URL + '/sendMessage'
    status = get_user_subscriptions(chat_id)
    
    message = "Статус подписок:\n"
    message += "Дубровка: {}\n".format("✅ Включено" if status['Dubrovka'] else "❌ Выключено")
    message += "Мята: {}\n".format("✅ Включено" if status['Mint'] else "❌ Выключено")
    
    keyboard = start_buttons_keyboard
    answer = {'chat_id': chat_id, 'text': message, 'reply_markup': keyboard}
    r = requests.post(url, json=answer)
    return r.json()

# В начале выполнения программы инициализируем БД
init_db()

if __name__ == '__main__':
    app.run()