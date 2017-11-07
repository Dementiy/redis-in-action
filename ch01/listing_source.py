import redis

ONE_WEEK_IN_SECONDS = 7 * 86400
VOTE_SCORE = 432
ARTICLES_PER_PAGE = 25


def article_vote(conn, user, article):
    """ Проголосовать за статью

    :param conn: Соединение с Redis
    :param user: Пользователь, который голосует
    :param article: Статья, за которую голосует пользователь
    """
    cutoff = time.time() - ONE_WEEK_IN_SECONDS
    # Проверяем, что статья была опубликована не более недели назад
    if conn.zscore('time:', article) < cutoff:
        return

    article_id = article.partition(':')[-1]
    # Добавляем голос пользователя, если он еще не голосовал за статью
    if conn.sadd('voted:' + article_id, user):
        # Увеличиваем score статьи
        conn.zincrby('score:', article, VOTE_SCORE)
        # Увеличиваем число голосов за статью
        conn.hincrby(article, 'votes', 1)


def post_article(conn, user, title, link):
    """ Публикация новой статьи

    :param conn: Соединение с Redis
    :param user: Пользователь публикующий статью
    :param title: Заголовок статьи
    :param link: Ссылка на статью
    """
    # Создание нового идентификатора статьи
    article_id = str(conn.incr('article:'))
    voted = 'voted:' + article_id

    # Пользователь опубликовавший статью за нее же голосует
    conn.sadd(voted, user)
    # Статья "протухает" через неделю
    conn.expire(voted, ONE_WEEK_IN_SECONDS)

    now = time.time()
    article = 'article:' + article_id

    # Добавляем статью
    conn.hmset(article, {
        'title': title,
        'link': link,
        'poster': user,
        'time': now,
        'votes': 1,
    })

    # Создаем запись с весом статьи, учитвая голос автора статьи
    conn.zadd('score:', article, now + VOTE_SCORE)
    # Создаем запись со временем публикации статьи
    conn.zadd('time:', article, now)

    return article_id


def get_articles(conn, page, order="score:"):
    """ Получить ранжированный список статей

    :param conn: Соединение с Redis
    :param page: Номер страницы
    :param order: Критерий ранжирования статей
    """
    start = (page - 1) * ARTICLES_PER_PAGE
    end = start + ARTICLES_PER_PAGE - 1
    # Получаем ранжированный список идентификаторов статей с указанной странцы
    ids = conn.zrevrange(order, start, end)

    # По идентификаторам получаем данные по самим статьям
    articles = []
    for id in ids:
        article_data = conn.hgetall(id)
        article_data['id'] = id
        articles.append(article_data)
    return articles


def add_remove_groups(conn, article_id, to_add=None, to_remove=None):
    """ Добавить или удалить статью из указанного списка групп

    :param conn: Соединение Redis
    :param article_id: Идентификатор статьи
    :param to_add: Список групп, в которые нужно добавить статью
    :param to_remove: Список групп, из которых нужно удалить статью
    """
    to_add = to_add or []
    to_remove = to_remove or []

    article = 'article:' + article_id
    for group in to_add:
        conn.sadd('group:' + group, article)

    for group in to_remove:
        conn.srem('group:' + group, article)


def get_group_articles(conn, group, page, order="score:"):
    """ Получить ранжированный список статей из указанной группы

    :param conn: Соединение с Redis
    :param group: Название группы
    :param page: Номер страницы
    :param order: Критерий ранжирования статей
    """
    key = order + group
    if not conn.exists(key):
        conn.zinterstore(key, ["group:" + group, order], aggregate="max")
        conn.expire(key, 60)
    return get_articles(conn, page, key)

