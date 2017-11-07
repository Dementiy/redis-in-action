from faker import Faker
import json
import argparse


def generate_articles(N):
    fake = Faker()
    articles = []
    for _ in range(N):
        article = {
            'user': fake.user_name(),
            'link': fake.url(),
            'title': fake.sentence()
        }
        articles.append(article)
    return articles


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', dest='N', type=int, default=10,
        help='number of articles')
    parser.add_argument('-f', dest='filename', default='articles.json',
        help='destination file')
    args = parser.parse_args()

    articles = generate_articles(args.N)
    with open(args.filename, 'w') as f:
        json.dump(articles, f)

