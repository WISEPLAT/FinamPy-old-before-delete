import time

from FinamPy.FinamPy import FinamPy
from FinamPy.Config import Config


if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    fp_provider = FinamPy(Config.AccessToken)  # Подключаемся

    symbols = (('TQBR', 'SBER'), ('FUT', 'SiM3'), ('FUT', 'RIM3'))  # Кортеж тикеров в виде (код площадки, код тикера)

    print('Получаем информацию обо всех тикерах (займет около 10-и секунд)...')
    securities = fp_provider.get_securities()  # Получаем информацию обо всех тикерах
    for board, symbol in symbols:  # Пробегаемся по всем тикерам
        si = next(item for item in securities.securities if item.board == board and item.code == symbol)
        # print('Ответ от сервера:', si)
        print(f'\nИнформация о тикере {si.board}.{si.code} ({si.short_name}, {fp_provider.markets[si.market]}):')
        print(f'Валюта: {si.currency}')
        decimals = si.decimals
        print(f'Кол-во десятичных знаков: {decimals}')
        print(f'Лот: {si.lot_size}')
        min_step = 10 ** -decimals * si.min_step
        print(f'Шаг цены: {min_step}')

    fp_provider.close_subscriptions_thread()  # Закрытие потока подписок перед выходом
