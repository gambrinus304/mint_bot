import requests
import datetime
from datetime import datetime


disco = {
        "Dubrovka": [
            {"date":"2025-10-25", "event":"tdd-bg",        "description": "ТДД Bg"},
            {"date":"2025-11-01", "event":"",           "description": ""},
            {"date":"2025-11-08", "event":"league",     "description": "Лига Дубровки"},
            {"date":"2025-11-15", "event":"",           "description": ""},
            {"date":"2025-11-22", "event":"tdd-bg",        "description": "ТДД Bg"},
            {"date":"2025-11-29", "event":"porosl",     "description": "Поросль Дубровки и вечеринка до 0:30 в ТЦ Нора (пр-т Андропова, 22)"},
            {"date":"2025-12-06", "event":"",           "description": ""},
            {"date":"2025-12-13", "event":"",           "description": "отмена дискотеки, ЧР"},
            {"date":"2025-12-20", "event":"multidance", "description": "Мультиденс"},
            {"date":"2025-12-27", "event":"tdd-bg",        "description": "возможно заключительный тур ТДД Bg"}
        ],
        "Mint": [
            {"date":"2025-10-26", "event":"junior",     "description": "Младшая лига"},
            {"date":"2025-11-02", "event":"",           "description": "Вечеринка 'День Мертвых'"},
            {"date":"2025-11-09", "event":"",           "description": ""},
            {"date":"2025-11-16", "event":"tdd-rs",     "description": "ТДД Rs"},
            {"date":"2025-11-23", "event":"junior",     "description": "Младшая лига"},
            {"date":"2025-12-07", "event":"",           "description": ""},
            {"date":"2025-12-14", "event":"",           "description": "Отмена дискотеки, ЧР"},
            {"date":"2025-12-21", "event":"",           "description": "Иваровский Новогодний вечер"},
            {"date":"2025-12-28", "event":"",           "description": "неизвестность царит в данной точке истории"}
        ]}


    
def next_disco(place):
    sorted_disco = sort_disco_dates()
    result = []
    
    if place.lower() == "all":
        # Собираем все события в один список
        all_events = []
        for location, events in sorted_disco.items():
            for event in events:
                all_events.append({
                    "place": location,
                    "date": event["date"],
                    "description": event["description"]
                })
        # Сортируем все события по дате
        all_events.sort(key=lambda x: datetime.strptime(x["date"], '%Y-%m-%d'))
        result = all_events[:4]  # Берем первые 4 события
    else:
        if place in sorted_disco:
            result = [{"place": place, "date": event["date"], "description": event["description"]} 
                     for event in sorted_disco[place][:4]]
    return result

def show_events_by_type(event_type):
    VALID_EVENTS = {
        "tdd-bg": "tdd-bg",
        "tdd-rs": "tdd-rs",
        "junior": "junior", 
        "league": "league",
        "multidance": "multidance",
        "porosl": "porosl",
        "all": "all"
    }
    
    if event_type.lower() not in VALID_EVENTS:
        return []
        
    sorted_disco = sort_disco_dates()
    all_events = []
    current_date = datetime.now().date()
    
    # Собираем все события в один список
    for location, events in sorted_disco.items():
        for event in events:
            event_date = datetime.strptime(event["date"], '%Y-%m-%d').date()
            if event_date >= current_date:  # Проверяем, что событие не прошло
                if event_type.lower() == "all":
                    # Для "all" показываем все события с непустым event
                    if event["event"] and event["event"] != "":
                        all_events.append({
                            "place": location,
                            "date": event["date"],
                            "event": event["description"]  # Используем description для отображения
                        })
                elif event["event"] == VALID_EVENTS[event_type.lower()]:
                    # Точное совпадение по типу события
                    all_events.append({
                        "place": location,
                        "date": event["date"],
                        "event": event["description"]  # Используем description для отображения
                    })
    
    # Сортируем по дате
    all_events.sort(key=lambda x: datetime.strptime(x["date"], '%Y-%m-%d'))
    return all_events





def sort_disco_dates():
    # Функция для преобразования строки даты в объект datetime
    def parse_date(date_str):
        return datetime.strptime(date_str, '%Y-%m-%d')
    
    # Создаем копию данных для сортировки
    sorted_disco = {}
    for place in disco:
        sorted_disco[place] = sorted(disco[place], key=lambda x: parse_date(x['date']))
    
    return sorted_disco


def main():
    # Примеры использования:
    # next_disco("all")
    # next_events = next_disco("all")
    # for event in next_events:
    #     print(f"{event['place']}: {event['date']}, {event['event']}")
        
    # tdd_events = show_events_by_type("тдд")
    # for event in tdd_events:
    #     print(f"{event['place']}: {event['date']}, {event['event']}")
    # show_events_by_type("all")
    pass
    

if __name__ == '__main__':
    main()
    
    
    
    
# # Сохранение в файл
# with open('disco.json', 'w', encoding='utf-8') as f:
#     json.dump(disco, f, ensure_ascii=False, indent=4)

# # Чтение из файла
# with open('disco.json', 'r', encoding='utf-8') as f:
#     disco = json.load(f)