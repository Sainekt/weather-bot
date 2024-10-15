import os
import requests
from dotenv import load_dotenv
from telebot import TeleBot
import json
from translate import TRANSLATE
load_dotenv()

API_KEY = os.getenv('api_key')
TG_KEY = os.getenv('tg_token')
HEADER = {'X-Yandex-Weather-Key': API_KEY}

URL = 'https://api.weather.yandex.ru/graphql/query'
URL_GEO_CODE = 'https://geocoding-api.open-meteo.com/v1/search?'


def get_lat_lon(city: str) -> tuple[str]:
    """Получаем  координаты города."""
    response = requests.get(
        f'{URL_GEO_CODE}name={city}&count=1&language=ru&format=json'
    )
    result = json.loads(response.content).get('results')
    if not result:
        return
    return str(result[0]['latitude']), str(result[0]['longitude'])


def get_query_params(coordinate: tuple[str]) -> str:
    """Получаем параметры запроса."""
    lat, lon = coordinate
    query = (
        '{weatherByPoint(request: {lat:' + lat + ', lon:' + lon + '}) {'
        'now {temperature humidity pressure windSpeed windDirection '
        'cloudiness precType precStrength}}}'
    )
    return query


def parse_response(content: bytes, time: str = 'now') -> str:
    """Парсим ответ от сервера, формирует ответ пользователю."""
    content = json.loads(content)
    result = (content['data']['weatherByPoint'][time])
    temperature = result.get('temperature')
    humidity = result.get('humidity')
    pressure = result.get('pressure')
    prec_type = result.get('precType')
    prec_strength = result.get('precStrength')
    wind_speed = result.get('windSpeed')
    wind_direction = result.get('windDirection')
    cloudiness = result.get('cloudiness')
    text = (
        f'Температура: {temperature} градусов.\n'
        f'Влажность: {humidity}%\n'
        f'Давление: {pressure}мм рт. ст.\n'
        f'Облачность: {TRANSLATE[cloudiness]}\n'
    )
    if (prec_strength := TRANSLATE[prec_strength]):
        text += f'Тип осадков: {prec_strength} {TRANSLATE[prec_type]}\n'
    text += f'Ветер: {TRANSLATE[wind_direction]} {wind_speed}м.с\n'
    return text


def main():
    bot = TeleBot(token=TG_KEY)

    @bot.message_handler(commands=['start'])
    def wake_up(message):
        text = (
            'Привет! Я бот, который может показать тебе погоду.\n'
            'просто напиши город :)'
        )
        bot.send_message(
            chat_id=message.chat.id,
            text=text,
        )

    @bot.message_handler(content_types=['text'])
    def get_params(message):
        chat_id = message.chat.id
        city = message.text
        if not (coodinate := get_lat_lon(city)):
            bot.send_message(
                chat_id=chat_id,
                text='Извините, но мы не нашли такой город :с')
            return
        query_params = get_query_params(coodinate)
        response = requests.post(
            URL, headers=HEADER, json={'query': query_params}
        )
        text = 'Погода в запрошенном городе:\n'
        text += parse_response(response.content)
        bot.send_message(chat_id=chat_id, text=text)

    while True:
        bot.polling()


if __name__ == '__main__':
    main()
