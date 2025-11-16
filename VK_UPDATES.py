import requests
import json
import csv
import os
import sys 
sys.path.append('..')
from time import sleep
import re


"""
    Имеющиеся проблемы/доработки:
    - обрабатывает только один тип вложений. Может сломаться если есть фото+аудио или фото+плейлист
    - нет обработки отредактированных постов. Думаю, стоит брать в работу только закрепленные(offset=0) и смотреть по pinned=1 и наличию edited 
"""

vk_token = '5f4523a95f4523a95f4523a98f5f343e1e55f455f4523a901d287cd356d46868a4bc53a'
Mint_id = '-127965281' 
Dubrovka_id = '-7959989' 
# user_id = '-143663305' #test group



dubrovka_anonse = None
mint_anonse = None


def get_post(group_id, offset):
    r = requests.get('https://api.vk.com/method/wall.get', params={'owner_id': group_id, 'v': 5.199, 'count': 1, 'offset': offset, 'access_token': vk_token})
    post_text = r.json()['response']['items'][0]['text']
    tg_post_text = re.sub(r'\[([^|]+)\|(.*?)\]', r'<a href="https://vk.com/\1">\2</a>', post_text)
    post_time = r.json()['response']['items'][0]['date']
    attachments = r.json()['response']['items'][0]['attachments']
    post_photos = 'empty'
    post_video = 'empty'
    video_cover = 'empty'
    post_audio = 'empty'
    post_link = 'empty'

    if not attachments:
        print('Нет вложений')
        return tg_post_text, 'empty', 'empty', 'empty', 'empty', 'empty', post_time

    # Проверяем первое вложение для определения типа
    attachment_type = attachments[0].get('type')
    print(f'Тип вложения: {attachment_type}')

    if attachment_type == 'photo':
        # print('Обработка фото')
        try:
            post_photos = []
            for idx, attachment in enumerate(attachments):
                if attachment.get('type') == 'photo':
                    media_item = {
                        'type': 'photo',
                        'media': attachment['photo']['orig_photo']['url'], 
                        'caption': tg_post_text if idx == 0 else '', # Добавляем текст поста только к первой фотографии
                        'parse_mode': 'HTML' if idx == 0 else ''
                    }
                    post_photos.append(media_item)
            # print(f'Найдено фото: {len(post_photos)}')
        except Exception as e:
            print(f'Ошибка при обработке фото: {e}')
            post_photos = 'empty'

    elif attachment_type == 'video':
        # print('Обработка видео')
        try:
            video_cover = attachments[0]['video']['image'][-1]['url']
            video_id = attachments[0]['video']['id']
            video_owner_id = attachments[0]['video']['owner_id']
            post_video = f'https://vk.com/video{video_owner_id}_{video_id}'
            # print(f'Видео найдено: {post_video}')
        except Exception as e:
            print(f'Ошибка при обработке видео: {e}')
            post_video = 'empty'
            video_cover = 'empty'

    elif attachment_type == 'audio':
        # print('Обработка аудио')
        try:
            all_tracks = []
            for attachment in attachments:
                if attachment.get('type') == 'audio':
                    audio = attachment['audio']
                    track = f"{audio.get('artist', '')} - {audio.get('title', '')}"
                    track_url = audio.get('url', '')
                    track_html = f'<a href="{track_url}">{track}</a>'
                    all_tracks.append(track_html)
            post_audio = '\n'.join(all_tracks)
            # print(f'Найдено аудио: {len(all_tracks)} треков')
        except Exception as e:
            print(f'Ошибка при обработке аудио: {e}')
            post_audio = 'empty'

    elif attachment_type == 'link':
        print('Найдена ссылка')
        try:
            post_link = attachments[0]['link']['url']
            print(post_link)
        except Exception as e:
            print(f'Ошибка при обработке ссылки: {e}')
            post_link = 'empty'
    

    else:
        print(f'Неизвестный тип вложения: {attachment_type}')
        return tg_post_text, 'empty', 'empty', 'empty', 'empty', 'empty', post_time

    return tg_post_text, post_photos, post_video, video_cover, post_audio, post_link, post_time



def delete_csv_entry(group_id):
    """
    Удаляет запись для указанного group_id из CSV файла.
    """
    filename = 'anonces.csv'
    
    if not os.path.exists(filename):
        print(f"Файл {filename} не существует, нечего удалять")
        return
    
    rows = []
    found = False
    
    # Читаем существующий файл
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 1 and row[0] == group_id:
                # Нашли запись для этого group_id - пропускаем (удаляем)
                found = True
                print(f"Удаляем запись для {group_id}")
            else:
                # Это запись для другого group_id - сохраняем
                rows.append(row)
    
    # Записываем обратно в файл только если была найдена и удалена запись
    if found:
        with open(filename, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        print(f"Запись для {group_id} удалена из файла {filename}")
    else:
        print(f"Запись для {group_id} не найдена в файле {filename}")


def write_csv(group_id, data_hash, data):
    """
    Записывает данные в CSV файл с проверкой хеша.
    Если для group_id уже есть запись с другим хешем - перезаписывает.
    Если хеш совпадает - оставляет без изменений.
    Если записи нет - добавляет новую.
    """
    
    filename = 'anonces.csv'
    rows = []
    found = False
    updated = False
    
    # Читаем существующий файл, если он есть
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2 and row[0] == group_id:
                    # Нашли запись для этого group_id
                    found = True
                    existing_hash = row[1] if len(row) > 1 else None
                    
                    # Сравниваем хеши
                    if existing_hash != data_hash:
                        # Хеши различаются - обновляем запись
                        print(f"Хеш для {group_id} изменился: {existing_hash} -> {data_hash}, обновляем запись")
                        rows.append([group_id, data_hash, json.dumps(data, ensure_ascii=False)])
                        updated = True
                    else:
                        # Хеши совпадают - оставляем старую запись
                        print(f"Хеш для {group_id} не изменился ({data_hash}), оставляем существующую запись")
                        rows.append(row)
                else:
                    # Это запись для другого group_id или пустая строка
                    rows.append(row)
    
    # Если запись не найдена, добавляем новую
    if not found:
        print(f"Новая запись для {group_id} с хешем {data_hash}")
        rows.append([group_id, data_hash, json.dumps(data, ensure_ascii=False)])
        updated = True
    
    # Записываем обратно в файл только если были изменения
    if updated or not os.path.exists(filename):
        with open(filename, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        print(f"Файл {filename} обновлен")
    else:
        print(f"Файл {filename} не требует изменений")




def get_anonse(group_id):
    r = requests.get('https://api.vk.com/method/wall.get', params={'owner_id': group_id, 'v': 5.199, 'count': 1, 'offset': 0, 'access_token': vk_token})
    # print(r.json())
    
    # Проверяем наличие закрепленного поста
    if r.json()['response']['items'][0].get('is_pinned') == 1:
        print('Обнаружен закрепленный пост')
        post_data = r.json()['response']['items'][0]
        data_hash = r.json()['response']['items'][0]['hash']

        # Сохраняем данные закрепленного поста
        data = {
            'group_id': group_id,
            'data_hash': data_hash,
            'post_data': post_data
        }
        write_csv(group_id, data_hash, data)
    else:
        # Если закрепленного поста нет - очищаем данные для этой группы
        print(f'Закрепленный пост для {group_id} не найден, очищаем данные')
        delete_csv_entry(group_id)


def main():
    get_anonse(Dubrovka_id)
    get_anonse(Mint_id)


    # r = requests.get('https://api.vk.com/method/wall.get', params={'owner_id': user_id, 'v': 5.199, 'count': 1, 'offset': 0, 'access_token': vk_token})
    # print(r.json())

    # #   post_object = vk_data.get('object', {})
    # if r.json()['response']['items'][0].get('is_pinned') == 1:
    #     print('Обнаружен закрепленный пост, сохраняем как анонс')
    #     dubrovka_anonse = get_post('-7959989', 0)
    #     print(dubrovka_anonse)
    # else:
    #    print('Закрепленный пост не найден')
    
    
    # try:
    #     mint_anonse = get_post(-127965281, 0)
    #     print('Mint anonse')
    #     print(mint_anonse)



    # dubrovka_last_post = get_post(-7959989, 1)
    # dubrovka_anonse = get_post(-7959989, 0)
 
    
    # attachments = r.json()['response']['items'][0]['attachments']
    
    # # Подсчитываем количество каждого типа вложений
    # attachment_types = {}
    # for attachment in attachments:
    #     att_type = attachment.get('type')
    #     attachment_types[att_type] = attachment_types.get(att_type, 0) + 1
    
    # print("Количество вложений по типам:", attachment_types)
    # post_text = r.json()['response']['items'][0]['text']
    # print(post_text)


if __name__ == '__main__':
    main()


