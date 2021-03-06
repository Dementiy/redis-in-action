Используемые "коллекции":
- `login:` - пользовательские сессии (`user:token`)
- `recent:` - множество, содержащее время последней активности пользователя (`token:timestamp`)
- `viewed:token` - множество последних просмотренных товаров пользователем (`item:timestamp`)
- `viewed:` - множество последних просмотренных товаров (`item:score`)
- `cart:token` - товары в корзине пользователя (`item:count`)
- `cache:hash` - содержимое некоторой страницы
- `schedule:` - список строк из БД подлежащих кешированию (`row_id:timestamp`)
- `delay:` - время, через которое строка `row_id` должна быть закеширована (`row_id:delay`)
- `inv:row_id` - закешированное содержимое строки из БД

Функция `add_to_cart` удаляет товар из корзины, если `count <= 0`, возможно лучше не удалять товар, а уменьшать его количество, например:
```
def add_to_cart(conn, session, item, count):
    nitems = conn.hget('cart:' + session, item)
    if nitems and count - int(nitems) <= 0:
        conn.hdel('cart:' + session, item)
    else:
        conn.hincrby('cart:' + session, item, count)
```

Функции `clean_sessions`, `clean_full_sessions`, `cache_rows`, `rescale_viewed` больше не полагаются на глобальные переменные `LIMIT` и `QUIT`. Так как автор предполагает, что каждая функция будет работать как демон, то в качестве одного из аргументов (`quit`) передается событие `threading.Event`, которое должно быть установлено, чтобы поток завершил свою работу (см. примеры в тестах).

