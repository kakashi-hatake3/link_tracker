# Конфигурация проекта

### Создайте .env файл в корне проекта 
Его структура находится в .env.example

### Тесты
Не забудьте запустить docker engine на компе, он нужен для testcontainers

### Запуск scrapper:
` poetry run python -m src.scrapper.app `

### Запуск телеграм бота:
`poetry run python -m src.server`

## Работа с ботом:
Перед работой с ботом нужно зарегистрироваться, то есть ввести команду /start