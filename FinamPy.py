from typing import Iterable
from threading import Thread, Event as ThreadingEvent  # Поток обработки подписок
from queue import Queue, Empty  # Очередь подписок/отписок
from grpc import ssl_channel_credentials, secure_channel  # Защищенный канал
from FinamPy.proto.tradeapi.v1.common_pb2 import Market  # Рынки
from FinamPy.proto.tradeapi.v1.events_pb2 import (
    SubscriptionRequest,
    OrderBookSubscribeRequest, OrderBookUnsubscribeRequest, OrderBookEvent,
    OrderTradeSubscribeRequest, OrderTradeUnsubscribeRequest, PortfolioEvent)
from FinamPy.grpc.tradeapi.v1.events_pb2_grpc import EventsStub
from FinamPy.proto.tradeapi.v1.orders_pb2 import GetOrdersRequest, GetOrdersResult
from FinamPy.grpc.tradeapi.v1.orders_pb2_grpc import OrdersStub
from FinamPy.proto.tradeapi.v1.portfolios_pb2 import PortfolioContent, GetPortfolioRequest, GetPortfolioResult
from FinamPy.grpc.tradeapi.v1.portfolios_pb2_grpc import PortfoliosStub
from FinamPy.grpc.tradeapi.v1.securities_pb2 import GetSecuritiesRequest, GetSecuritiesResult
from FinamPy.grpc.tradeapi.v1.securities_pb2_grpc import SecuritiesStub
from FinamPy.proto.tradeapi.v1.stops_pb2 import GetStopsRequest, GetStopsResult
from FinamPy.grpc.tradeapi.v1.stops_pb2_grpc import StopsStub


class FinamPy:
    """Работа с сервером TRANSAQ из Python через REST/gRPC
    Документация интерфейса Finam Trade API: https://finamweb.github.io/trade-api-docs/
    Генерация кода в папках grpc/proto осуществлена из proto контрактов: https://github.com/FinamWeb/trade-api-docs/tree/master/contracts
    """
    server = 'trade-api.finam.ru'  # Сервер для исполнения вызовов
    markets = {Market.MARKET_STOCK: 'Фондовый рынок Московской Биржи',
               Market.MARKET_FORTS: 'Срочный рынок Московской Биржи',
               Market.MARKET_SPBEX: 'Санкт-Петербургская биржа',
               Market.MARKET_MMA: 'Фондовый рынок США',
               Market.MARKET_ETS: 'Валютный рынок Московской Биржи',
               Market.MARKET_BONDS: 'Долговой рынок Московской Биржи',
               Market.MARKET_OPTIONS: 'Рынок опционов Московской Биржи'}  # Рынки

    def default_handler(self, event=None):
        """Пустой обработчик события по умолчанию. Его можно заменить на пользовательский"""
        pass

    def request_iterator(self) -> Iterable[SubscriptionRequest]:
        """Генератор запросов на подписку/отписку"""
        print('begin')  # DEBUG
        while not self.unsubscribe_event.is_set() or not self.subscription_queue.empty():  # Пока не было отписки или в очереди команд что-то есть
            try:
                request = self.subscription_queue.get(timeout=1)  # Пытаемся получить значение из очереди команд в течение 1 с
                print(request)  # DEBUG
            except Empty:  # Если в очереди команд значений нет
                pass
                print('empty')  # DEBUG
            else:
                yield request  # Возврат из этой функции. При повторном ее вызове исполнение продолжится с этой строки
        print('end')  # DEBUG

    def subscribtions_handler(self):
        """Поток обработки подписок"""
        events = self.events_stub.GetEvents(request_iterator=self.request_iterator(), metadata=self.metadata)  # Получаем подписки
        for event in events:  # FIXME Подписки не приходят. Дальше этой точки программа не идет
            if type(event) == OrderBookEvent:  # Событие стакана
                self.on_order_book(event)
            elif type(event) == PortfolioEvent:  # Событие портфеля
                self.on_portfolio(event)

    def __init__(self, access_token):
        """Инициализация

        :param str access_token: Торговый токен доступа
        """
        self.metadata = [('x-api-key', access_token)]  # Торговый токен доступа
        channel = secure_channel(self.server, ssl_channel_credentials())

        self.events_stub = EventsStub(channel)  # Сервис событий
        self.orders_stub = OrdersStub(channel)  # Сервис заявок
        self.portfolios_stub = PortfoliosStub(channel)  # Сервис портфелей
        self.securities_stub = SecuritiesStub(channel)  # Сервис тикеров
        self.stops_stub = StopsStub(channel)  # Сервис стоп заявок

        # События Finam Trade API
        self.on_order_book = self.default_handler  # Стакан
        self.on_portfolio = self.default_handler  # Портфель

        self.subscription_queue: Queue[SubscriptionRequest] = Queue()  # Буфер команд на подписку/отписку
        self.unsubscribe_event = ThreadingEvent()  # Событие отписки от всех подписок
        self.subscriptions_thread = Thread(target=self.subscribtions_handler, name='SubscriptionsThread')  # Создаем поток обработки подписок
        self.subscriptions_thread.start()  # Запускаем поток

    # Events

    def subscribe_order_book(self, request_id, security_code, security_board):
        """Запрос подписки на стакан

        :param str request_id: Идентификатор запроса
        :param str security_code: Тикер инструмента
        :param str security_board: Режим торгов
        """
        self.subscription_queue.put(OrderBookSubscribeRequest(request_id=request_id, security_code=security_code, security_board=security_board))

    def unsubscribe_order_book(self, request_id, security_code, security_board):
        """Запрос на отписку от стакана

        :param str request_id: Идентификатор запроса
        :param str security_code: Тикер инструмента
        :param str security_board: Режим торгов
        """
        self.subscription_queue.put(OrderBookUnsubscribeRequest(request_id=request_id, security_code=security_code, security_board=security_board))

    def subscribe_order_trade(self, request_id, client_ids, include_trades=True, include_orders=True):
        """Запрос подписки на ордера и сделки

        :param str request_id: Идентификатор запроса
        :param list client_ids: Торговые коды счетов
        :param bool include_trades: Включить сделки в подписку
        :param bool include_orders: Включить заявки в подписку
        """
        self.subscription_queue.put(OrderTradeSubscribeRequest(request_id=request_id, client_ids=client_ids, include_trades=include_trades, include_orders=include_orders))

    def unsubscribe_order_trade(self, request_id):
        """Отменить все предыдущие запросы на подписки на ордера и сделки

        :param str request_id: Идентификатор запроса
        """
        self.subscription_queue.put(OrderTradeUnsubscribeRequest(request_id=request_id))

    # Orders

    def get_orders(self, client_id, include_matched=True, include_canceled=True, include_active=True) -> GetOrdersResult:
        """Возвращает список заявок

        :param str client_id: Идентификатор торгового счёта
        :param bool include_matched: Вернуть исполненные заявки
        :param bool include_canceled: Вернуть отмененные заявки
        :param bool include_active: Вернуть активные заявки
        """
        request = GetOrdersRequest(client_id=client_id, include_matched=include_matched, include_canceled=include_canceled, include_active=include_active)
        response, call = self.orders_stub.GetOrders.with_call(request=request, metadata=self.metadata)
        return response

    # Portfolios

    def get_portfolio(self, client_id, include_currencies=True, include_money=True, include_positions=True, include_max_buy_sell=True) -> GetPortfolioResult:
        """Возвращает портфель

        :param str client_id: Идентификатор торгового счёта
        :param bool include_currencies: Валютные позиции
        :param bool include_money: Денежные позиции
        :param bool include_positions: Позиции DEPO
        :param bool include_max_buy_sell: Лимиты покупки и продажи
        """
        request = GetPortfolioRequest(client_id=client_id, content=PortfolioContent(
            include_currencies=include_currencies,
            include_money=include_money,
            include_positions=include_positions,
            include_max_buy_sell=include_max_buy_sell))
        response, call = self.portfolios_stub.GetPortfolio.with_call(request=request, metadata=self.metadata)
        return response

    # Securities

    def get_securities(self) -> GetSecuritiesResult:
        """Справочник инструментов"""
        request = GetSecuritiesRequest()
        response, call = self.securities_stub.GetSecurities.with_call(request=request, metadata=self.metadata)
        return response

    # Stops

    def get_stop_orders(self, client_id, include_executed=True, include_canceled=True, include_active=True) -> GetStopsResult:
        """Возвращает список стоп-заявок

        :param str client_id: Идентификатор торгового счёта
        :param bool include_executed: Вернуть исполненные стоп-заявки
        :param bool include_canceled: Вернуть отмененные стоп-заявки
        :param bool include_active: Вернуть активные стоп-заявки
        """
        request = GetStopsRequest(client_id=client_id, include_executed=include_executed, include_canceled=include_canceled, include_active=include_active)
        response, call = self.stops_stub.GetStops.with_call(request=request, metadata=self.metadata)
        return response

    # Выход и закрытие

    def close_subscriptions_thread(self):
        """Закрытие потока подписок"""
        self.unsubscribe_event.set()  # Выход из генератора, который приводит к окончанию приема событий и закрытию потока подписок

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_subscriptions_thread()

    def __del__(self):
        self.close_subscriptions_thread()
