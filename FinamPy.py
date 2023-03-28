from threading import Thread  # Поток обработки подписок
from queue import SimpleQueue  # Очередь подписок/отписок
from grpc import ssl_channel_credentials, secure_channel, RpcError  # Защищенный канал
from .proto.tradeapi.v1.common_pb2 import Market, OrderValidBefore, OrderValidBeforeType  # Рынки
from .proto.tradeapi.v1.events_pb2 import (
    SubscriptionRequest,
    OrderBookSubscribeRequest, OrderBookUnsubscribeRequest, OrderBookEvent,
    OrderTradeSubscribeRequest, OrderTradeUnsubscribeRequest, PortfolioEvent)  # Подписки
from .grpc.tradeapi.v1.events_pb2_grpc import EventsStub  # Сервис подписок
from .proto.tradeapi.v1.orders_pb2 import (
    GetOrdersRequest, GetOrdersResult,
    OrderProperty, OrderCondition, NewOrderRequest, NewOrderResult,
    CancelOrderRequest, CancelOrderResult)  # Заявки
from .grpc.tradeapi.v1.orders_pb2_grpc import OrdersStub  # Сервис заявок
from .proto.tradeapi.v1.portfolios_pb2 import PortfolioContent, GetPortfolioRequest, GetPortfolioResult  # Портфель
from .grpc.tradeapi.v1.portfolios_pb2_grpc import PortfoliosStub  # Сервис портфелей
from .grpc.tradeapi.v1.securities_pb2 import GetSecuritiesRequest, GetSecuritiesResult  # Тикеры
from .grpc.tradeapi.v1.securities_pb2_grpc import SecuritiesStub  # Сервис тикеров
from .proto.tradeapi.v1.stops_pb2 import (
    GetStopsRequest, GetStopsResult,
    StopLoss, TakeProfit, StopPrice, StopQuantity, StopQuantityUnits, StopPriceUnits, NewStopRequest, NewStopResult,
    CancelStopRequest, CancelStopResult)   # Стоп заявки
from .grpc.tradeapi.v1.stops_pb2_grpc import StopsStub  # Сервис стоп заявок


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

    def request_iterator(self):
        """Генератор запросов на подписку/отписку"""
        while True:  # Будем пытаться читать из очереди до закрытии канала
            yield self.subscription_queue.get()  # Возврат из этой функции. При повторном ее вызове исполнение продолжится с этой строки

    def subscribtions_handler(self):
        """Поток обработки подписок"""
        events = self.events_stub.GetEvents(request_iterator=self.request_iterator(), metadata=self.metadata)  # Получаем значения подписок
        try:
            for event in events:  # Пробегаемся по значениям подписок до закрытия канала
                if event.order_book != OrderBookEvent():  # Событие стакана
                    self.on_order_book(event)
                if event.portfolio != PortfolioEvent():  # Событие портфеля
                    self.on_portfolio(event)
        except RpcError:  # При закрытии канала попадем на эту ошибку (grpc._channel._MultiThreadedRendezvous)
            pass  # Все в порядке, ничего делать не нужно

    def __init__(self, access_token):
        """Инициализация

        :param str access_token: Торговый токен доступа
        """
        self.metadata = [('x-api-key', access_token)]  # Торговый токен доступа
        self.channel = secure_channel(self.server, ssl_channel_credentials())  # Защищенный канал

        # Сервисы
        self.events_stub = EventsStub(self.channel)  # Сервис событий
        self.orders_stub = OrdersStub(self.channel)  # Сервис заявок
        self.portfolios_stub = PortfoliosStub(self.channel)  # Сервис портфелей
        self.securities_stub = SecuritiesStub(self.channel)  # Сервис тикеров
        self.stops_stub = StopsStub(self.channel)  # Сервис стоп заявок

        # События Finam Trade API
        self.on_order_book = self.default_handler  # Стакан
        self.on_portfolio = self.default_handler  # Портфель

        self.subscription_queue: SimpleQueue[SubscriptionRequest] = SimpleQueue()  # Буфер команд на подписку/отписку
        self.subscriptions_thread = Thread(target=self.subscribtions_handler, name='SubscriptionsThread')  # Создаем поток обработки подписок
        self.subscriptions_thread.start()  # Запускаем поток

    # Запросы

    def call_function(self, func, request):
        """Вызов функции"""
        try:  # Пытаемся
            response, call = func.with_call(request=request, metadata=self.metadata)  # вызвать функцию
            return response  # и вернуть ответ
        except RpcError:  # Если получили ошибку канала
            return None  # то возвращаем пустое значение

    # Events

    def subscribe_order_book(self, request_id, security_code, security_board):
        """Запрос подписки на стакан

        :param str request_id: Идентификатор запроса
        :param str security_code: Тикер инструмента
        :param str security_board: Режим торгов
        """
        self.subscription_queue.put(SubscriptionRequest(order_book_subscribe_request=OrderBookSubscribeRequest(
            request_id=request_id, security_code=security_code, security_board=security_board)))

    def unsubscribe_order_book(self, request_id, security_code, security_board):
        """Запрос на отписку от стакана

        :param str request_id: Идентификатор запроса
        :param str security_code: Тикер инструмента
        :param str security_board: Режим торгов
        """
        self.subscription_queue.put(SubscriptionRequest(order_book_unsubscribe_request=OrderBookUnsubscribeRequest(
            request_id=request_id, security_code=security_code, security_board=security_board)))

    def subscribe_order_trade(self, request_id, client_ids, include_trades=True, include_orders=True):
        """Запрос подписки на ордера и сделки

        :param str request_id: Идентификатор запроса
        :param list client_ids: Торговые коды счетов
        :param bool include_trades: Включить сделки в подписку
        :param bool include_orders: Включить заявки в подписку
        """
        self.subscription_queue.put(SubscriptionRequest(order_trade_subscribe_request=OrderTradeSubscribeRequest(
            request_id=request_id, client_ids=client_ids, include_trades=include_trades, include_orders=include_orders)))

    def unsubscribe_order_trade(self, request_id):
        """Отменить все предыдущие запросы на подписки на ордера и сделки

        :param str request_id: Идентификатор запроса
        """
        self.subscription_queue.put(SubscriptionRequest(order_trade_unsubscribe_request=OrderTradeUnsubscribeRequest(
            request_id=request_id)))

    # Orders

    def get_orders(self, client_id, include_matched=True, include_canceled=True, include_active=True) -> GetOrdersResult | None:
        """Возвращает список заявок

        :param str client_id: Идентификатор торгового счёта
        :param bool include_matched: Вернуть исполненные заявки
        :param bool include_canceled: Вернуть отмененные заявки
        :param bool include_active: Вернуть активные заявки
        """
        request = GetOrdersRequest(client_id=client_id, include_matched=include_matched, include_canceled=include_canceled, include_active=include_active)
        return self.call_function(self.orders_stub.GetOrders, request)

    def new_order(self, client_id, security_board, security_code, buy_sell, quantity, use_credit, price, property: OrderProperty,
                  condition_type: OrderCondition, condition_price, condition_time, valid_type: OrderValidBeforeType, valid_time) -> NewOrderResult | None:
        """Создать новую заявку

        :param str client_id: Идентификатор торгового счёта
        :param str security_board: Режим торгов
        :param str security_code: Тикер инструмента
        :param str buy_sell: Направление сделки
            'Buy' - покупка
            'Sell' - продажа
        :param int quantity: Количество лотов инструмента для заявки
        :param bool use_credit: Использовать кредит. Недоступно для срочного рынка
        :param float price: Цена заявки. 0 для рыночной заявки
        :param str property: Поведение заявки при выставлении в стакан
            'PutInQueue' - Неисполненная часть заявки помещается в очередь заявок Биржи
            'CancelBalance' - (FOK) Сделки совершаются только в том случае, если заявка может быть удовлетворена полностью
            'ImmOrCancel' - (IOC) Неисполненная часть заявки снимается с торгов
        :param str condition_type: Типы условных ордеров
            'Bid' - Лучшая цена покупки
            'BidOrLast' - Лучшая цена покупки или сделка по заданной цене и выше
            'Ask' - Лучшая цена продажи
            'AskOrLast' - Лучшая цена продажи или сделка по заданной цене и ниже
            'Time' - По времени (valid_type)
            'CovDown' - Обеспеченность ниже заданной
            'CovUp' - Обеспеченность выше заданной
            'LastUp' - Сделка на рынке по заданной цене или выше
            'LastDown' - Сделка на рынке по заданной цене или ниже
        :param float condition_price: Значение цены для условия
        :param str condition_time: Время, когда заявка была отменена на сервере. В UTC
        :param str valid_type: Установка временнЫх рамок действия заявки
            'TillEndSession' - До окончания текущей сессии
            'TillCancelled' - До отмены
            'ExactTime' - До заданного времени (valid_time)
        :param str valid_time: Время, когда заявка была отменена на сервере. В UTC
        """
        request = NewOrderRequest(client_id=client_id, security_board=security_board, security_code=security_code,
                                  buy_sell=buy_sell, quantity=quantity, use_credit=use_credit, price=price, property=property,
                                  condition=OrderCondition(type=condition_type, price=condition_price, time=condition_time),
                                  valid_before=OrderValidBefore(type=valid_type, time=valid_time))
        return self.call_function(self.orders_stub.NewOrder, request)

    def cancel_order(self, client_id, transaction_id) -> CancelOrderResult | None:
        """Отменяет заявку

        :param str client_id: Идентификатор торгового счёта
        :param int transaction_id: Идентификатор транзакции, который может быть использован для отмены заявки или определения номера заявки в сервисе событий
        """
        request = CancelOrderRequest(client_id=client_id, transaction_id=transaction_id)
        return self.call_function(self.orders_stub.CancelOrder, request)

        # Portfolios

    def get_portfolio(self, client_id, include_currencies=True, include_money=True, include_positions=True, include_max_buy_sell=True) -> GetPortfolioResult | None:
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
        return self.call_function(self.portfolios_stub.GetPortfolio, request)

    # Securities

    def get_securities(self) -> GetSecuritiesResult | None:
        """Справочник инструментов"""
        request = GetSecuritiesRequest()
        return self.call_function(self.securities_stub.GetSecurities, request)

    # Stops

    def get_stops(self, client_id, include_executed=True, include_canceled=True, include_active=True) -> GetStopsResult | None:
        """Возвращает список стоп-заявок

        :param str client_id: Идентификатор торгового счёта
        :param bool include_executed: Вернуть исполненные стоп-заявки
        :param bool include_canceled: Вернуть отмененные стоп-заявки
        :param bool include_active: Вернуть активные стоп-заявки
        """
        request = GetStopsRequest(client_id=client_id, include_executed=include_executed, include_canceled=include_canceled, include_active=include_active)
        return self.call_function(self.stops_stub.GetStops, request)

    def new_stop(self, client_id, security_board, security_code, buy_sell,
                 sl_activation_price, sl_price, sl_market_price, sl_value, sl_units: StopQuantityUnits, sl_time, sl_use_credit,
                 tp_activation_price, tp_correction_price_value, tp_correction_price_units: StopPriceUnits, tp_spread_price_value, tp_spread_price_units: StopPriceUnits,
                 tp_market_price, tp_quantity_value, tp_quantity_units: StopQuantityUnits, tp_time, tp_use_credit,
                 expiration_date, link_order, valid_type: OrderValidBeforeType, valid_time) -> NewStopResult | None:
        """Выставляет стоп-заявку

        :param str client_id: Идентификатор торгового счёта
        :param str security_board: Режим торгов
        :param str security_code: Тикер инструмента
        :param str buy_sell: Направление сделки
            'Buy' - покупка
            'Sell' - продажа
        :param float sl_activation_price: Цена активации
        :param float sl_price: Цена заявки
        :param bool sl_market_price: По рынку
        :param float sl_value: Значение объема стоп-заявки
        :param str sl_units: Единицы объема стоп-заявки
            'Percent' - Процент
            'Lots' - Лоты
        :param int sl_time: Защитное время, сек.
        :param bool sl_use_credit: Использовать кредит
        :param float tp_activation_price: Цена активации
        :param float tp_correction_price_value: Значение цены стоп-заявки
        :param str tp_correction_price_units: Единицы цены стоп-заявки
            'Percent' - Процент
            'Pips' - Шаги цены
        :param float tp_spread_price_value: Значение цены стоп-заявки
        :param str tp_spread_price_units: Единицы цены стоп-заявки
            'Percent' - Процент
            'Pips' - Шаги цены
        :param bool tp_market_price: По рынку
        :param float tp_quantity_value: Значение объема стоп-заявки
        :param str tp_quantity_units: Единицы объема стоп-заявки
            'Percent' - Процент
            'Lots' - Лоты
        :param int tp_time: Защитное время, сек.
        :param bool tp_use_credit: Использовать кредит
        :param str expiration_date: Время, когда заявка была отменена на сервере. В UTC
        :param int link_order: Биржевой номер связанной (активной) заявки
        :param str valid_type: Установка временнЫх рамок действия заявки
            'TillEndSession' - До окончания текущей сессии
            'TillCancelled' - До отмены
            'ExactTime' - До заданного времени (valid_time)
        :param str valid_time: Время, когда заявка была отменена на сервере. В UTC
        """
        request = NewStopRequest(client_id=client_id, security_board=security_board, security_code=security_code, buy_sell=buy_sell,
                                 stop_loss=StopLoss(activation_price=sl_activation_price, price=sl_price, market_price=sl_market_price,
                                                    quantity=StopQuantity(value=sl_value, units=sl_units), time=sl_time, use_credit=sl_use_credit),
                                 take_profit=TakeProfit(activation_price=tp_activation_price,
                                                        correction_price=StopPrice(value=tp_correction_price_value, units=tp_correction_price_units),
                                                        spread_price=StopPrice(value=tp_spread_price_value, units=tp_spread_price_units),
                                                        market_price=tp_market_price, quantity=StopQuantity(value=tp_quantity_value, units=tp_quantity_units),
                                                        time=tp_time, use_credit=tp_use_credit),
                                 expiration_date=expiration_date, link_order=link_order, valid_before=OrderValidBefore(type=valid_type, time=valid_time))
        return self.call_function(self.stops_stub.NewStop, request)

    def cancel_stop(self, client_id, stop_id) -> CancelStopResult | None:
        """Снимает стоп-заявку

        :param str client_id: Идентификатор торгового счёта
        :param int stop_id: Идентификатор стоп-заявки
        """
        request = CancelStopRequest(client_id=client_id, stop_id=stop_id)
        return self.call_function(self.stops_stub.CancelStop, request)

    # Выход и закрытие

    def close_subscriptions_thread(self):
        """Закрытие потока подписок"""
        self.channel.close()  # Принудительно закрываем канал

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_subscriptions_thread()

    def __del__(self):
        self.close_subscriptions_thread()
