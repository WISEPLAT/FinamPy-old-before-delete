from FinamPy import FinamPy
from FinamPy.Config import Config


if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    fp_provider = FinamPy(Config.ClientId, Config.AccessToken)  # Подключаемся к торговому счету

    board = 'TQBR'  # Основной режим торгов инструмента
    symbol = 'SBER'  # Тикер
    # board = 'FUT'  # Основной режим торгов инструмента
    # symbol = 'SiH3'  # Тикер можно искать по короткому имени. Для фьючерсов: <Код тикера><Месяц экспирации: 3-H, 6-M, 9-U, 12-Z><Последняя цифра года>
    # symbol = 'RIH3'

    # Данные тикера и его торговый счет
    securities = fp_provider.get_securities()  # Получаем информацию о тикерах
    si = next(item for item in securities['securities'] if item['board'] == board and item['code'] == symbol)
    print('Ответ от сервера:', si)
    print(f'Информация о тикере {si["board"]}.{si["code"]} ({si["shortName"]}, {si["market"]}):')
    print(f'Валюта: {si["currency"]}')
    decimals = si["decimals"]
    print(f'Кол-во десятичных знаков: {decimals}')
    print(f'Лот: {si["lotSize"]}')
    min_step = 10 ** -decimals * si["minStep"]
    print(f'Шаг цены: {min_step}')
