from FinamPy import FinamPy
from FinamPy.Config import Config

if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    fp_provider = FinamPy(Config.AccessToken)  # Подключаемся к торговому счету. Идентификатор торгового счёта и торговый токен доступа берутся из файла Config.py
    fp_provider2 = FinamPy(Config.AccessToken)  # Для каждого счета будет создан свой экземпляр FinamPy
    print(f'Экземпляры класса совпадают: {fp_provider2 is fp_provider}')

    fp_provider.close_subscriptions_thread()  # Закрытие потока подписок перед выходом
    fp_provider2.close_subscriptions_thread()  # Закрытие потока подписок перед выходом
