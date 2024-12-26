from loguru import logger

from scorecard_validation.bandit_on_repo import bandit_on_repo


def main():
    bandit_on_repo("git@github.com:fastapi/fastapi.git")


if __name__ == '__main__':
    main()
