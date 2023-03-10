from FinamPy import FinamPy
from FinamPy.Config import Config

if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    fp_providers = []
    fp_providers.append((Config.ClientId, Config.AccessToken,))  # Торговый счет

    for client_id, access_token in fp_providers:  # Пробегаемся по всем счетам
        print(f'Учетная запись: {client_id}')
        fp_provider = FinamPy(client_id, access_token)  # Подключаемся к торговому счету
        portfolio = fp_provider.get_portfolio()  # Получаем портфель
        for position in portfolio['positions']:  # Пробегаемся по всем позициям
            print(f'  - Позиция ({position["securityCode"]}) {position["balance"]} @ {position["averagePrice"]:.2f} / {position["currentPrice"]:.2f}')
        print('  - Позиции + Свободные средства:')
        for currency in portfolio['currencies']:
            print(f'    - {currency["balance"]:.2f} {currency["name"]}')
        print('  - Свободные средства:')
        for m in portfolio['money']:
            print(f'    - {m["balance"]:.2f} {m["currency"]}')
        orders = fp_provider.get_orders()['orders']  # Получаем заявки
        for order in orders:  # Пробегаемся по всем заявкам
            print(f'  - Заявка номер {order["orderNo"]} {"Покупка" if order["buySell"] == "Buy" else "Продажа"} {order["securityBoard"]}.{order["securityCode"]} {order["quantity"]} @ {order["price"]}')
        stop_orders = fp_provider.get_stop_orders()['orders']  # Получаем стоп заявки
        for stop_order in stop_orders:  # Пробегаемся по всем стоп заявкам
            print(f'  - Стоп заявка номер {stop_order["stopId"]} {"Покупка" if stop_order["buySell"] == "Buy" else "Продажа"} {stop_order["securityBoard"]}.{stop_order["securityCode"]} {stop_order["quantity"]} @ {stop_order["price"]}')
