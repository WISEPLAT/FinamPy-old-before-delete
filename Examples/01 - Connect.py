from FinamPy import FinamPy
from FinamPy.Config import Config

if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    fp_provider = FinamPy(Config.AccessToken)  # Подключаемся к торговому счету. Идентификатор торгового счёта и торговый токен доступа берутся из файла Config.py
    fp_provider2 = FinamPy(Config.AccessToken)  # Для каждого счета будет создан свой экземпляр FinamPy
    print(f'Экземпляры класса совпадают: {fp_provider2 is fp_provider}')
    fp_provider2.close_subscriptions_thread()  # Закрытие потока подписок перед выходом

    fp_provider.on_order_book = lambda event: print('ask:', event.order_book.asks[0].price, 'bid:', event.order_book.bids[-1].price)  # Обработчик события прихода подписки на стакан

    # Получаем подписку стакана
    security_board = 'TQBR'  # Код площадки
    security_code = 'SBER'  # Тикер
    print(f'Подписка на стакан тикера: {security_board}.{security_code}')
    fp_provider.subscribe_order_book(request_id='orderbook1', security_code=security_code, security_board=security_board)  # Подписываемся на стакан тикера

    # Выход
    input('Enter - выход\n')
    fp_provider.unsubscribe_order_book('orderbook1', 'SBER', 'TQBR')  # Отписываемся от стакана тикера
    fp_provider.close_subscriptions_thread()  # Закрытие потока подписок перед выходом
