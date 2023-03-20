import time

from FinamPy.FinamPy import FinamPy
from FinamPy.Config import Config


if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    fp_provider = FinamPy(Config.AccessToken)  # Подключаемся
    fp_provider.on_order_book = lambda event: print(event)  # Обработчик события прихода подписки на стакан

    fp_provider.subscribe_order_book('orderbook1', 'SBER', 'TQBR')  # Подписываемся на стакан тикера
    time.sleep(5)  # Получаем стакан 5 секунд
    fp_provider.unsubscribe_order_book('orderbook1', 'SBER', 'TQBR')  # Отписываемся от стакана тикера

    fp_provider.close_subscriptions_thread()  # Закрытие потока подписок перед выходом
