# Собственный tcp-сервер может пригодиться  при написании командных оболочек или прокси-серверов. Для начала создадим
# Стандартный многопоточный tcp-сервер

import socket
import threading

IP = '0.0.0.0'
PORT = 9998


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((IP, PORT))  # 1 вначале мы передаем ip-адрес и порт, который должен прослушивать наш сервер
    server.listen(5)  # 2 здесь просим сервер начать прослушивание указав что отложженных соединений должно быть
    print(f'[*] Listening on {IP}: {PORT}')  # не больше пяти

    while True:  # 3 затем сервер входит в главный цикл, в котором ждет входящее соединение
        client, address = server.accept()  # в переменной client мы пполучаем клиентский сокет, и подроьности об
        
        print(f'[*] Accepted connection from {address[0]}:{address[1]}')
        client_handler = threading.Thread(target=handle_client, args=(client,))
        client_handler.start()  # 4


def handle_client(client_socket):  # 5
    with client_socket as sock:
        request = sock.recv(1024)
        print(f'[*] Received: {request.decode("utf-8")} ')
        sock.send(b'ACK')


if __name__ == '__main__':
    main()
