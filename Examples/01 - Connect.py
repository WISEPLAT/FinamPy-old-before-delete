from FinamPy import FinamPy
from FinamPy.Config import Config

if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    fp_provider = FinamPy(Config.ClientId, Config.AccessToken)  # Подключаемся к торговому счету. Идентификатор торгового счёта и торговый токен доступа берутся из файла Config.py
    fp_provider2 = FinamPy(Config.ClientId, Config.AccessToken)  # Для каждого счета будет создан свой экземпляр FinamPy
    print(f'Экземпляры класса совпадают: {fp_provider2 is fp_provider}')

    fp_provider.OnError = lambda response: print(response)  # Обработка ошибок

    # Проверяем работу API запрос/ответ. Проверяем токен доступа
    print('Номер подключения:', fp_provider.check_access_token()['id'])
