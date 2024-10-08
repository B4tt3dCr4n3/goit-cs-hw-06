# Технічний опис завдання

Вам необхідно реалізувати найпростіший вебдодаток, не використовуючи вебфреймворк.

## Інструкція та вимоги до виконання

За аналогією до розглянутого в конспекті прикладу, створіть вебдодаток з маршрутизацією для двох html-сторінок: `index.html` та `message.html`. За основу візьміть наступні файли.

### Також:

- Обробіть під час роботи програми статичні ресурси: `style.css`, `logo.png`.
- Організуйте роботу з формою на сторінці `message.html`.
- У разі виникнення помилки 404 Not Found повертайте сторінку `error.html`.
- Ваш HTTP-сервер повинен працювати на порту `3000`.

### Робота з Socket-сервером:

Для роботи з формою створіть Socket-сервер на порту `5000`. Алгоритм роботи:

1. Вводите дані у форму.
2. Вони потрапляють у вебдодаток, який пересилає їх далі на обробку за допомогою socket (протокол UDP або TCP на ваш вибір) Socket-серверу.
3. Socket-сервер переводить отриманий байт-рядок у словник і зберігає його в базу даних MongoDB.

Формат запису документа MongoDB має бути наступного вигляду:

```json
{
  "date": "2022-10-29 20:20:58.020261",
  "username": "krabaton",
  "message": "First message"
}
{
  "date": "2022-10-29 20:21:11.812177",
  "username": "Krabat",
  "message": "Second message"
}
