"""Есть несколько причин иметь в своем арсенале tcp-прокси. Его можно использовать для перенаправления трафика от
узла к узлу или для доступа к сетевому ПО. При выполнении тестирования на проникновение в корпоративных средах,
скорее всего, не будет возможности запустить Wireshark, также не сможем загрузить драйверы для анализа трафика
на локальном сетевом интерфейсе в windows, а сегментация сети не даст нам применить свои инструменты непосредсвенно
на атакуемом компьютере.
Прокси-сервер состоит из нескольких частей. Сейчас быстро пройдемся по четырем главным функциям, которые нужно
напсиать. Мы должны выводить взаимодействие между локальной и удаленной системами в консоль (hexdump). Нам нужно
принимать данные от локальной или удаленной системы с помощью входящего сокета (receive_from). Мы должны определять
направление трафика, которым обмениваются локальная и удаленная системы (proxy_handler). И наконец, должны подготовить
слушающий сокет и передать его нашей функции proxy_handler(server_loop)"""

import sys
import socket
import threading

"""Сначала мы импортируем несколько модулей. Затем определяем функцию hexdump, которая принимает ввод в виде байтов
и выводит его в консоль в шестнадцатиричном формате. То есть она показывает содержимое пакетов и как 
шестнадцатиричные значения, и как печатные символы ASCII. Это помогоает разобраться в неизвестных протоколах, 
обнаружить учетные данные пользователей, если взаимодействие не зашифорвано, и многое другое."""

HEX_FILTER = ''.join([(len(repr(chr(i))) == 3) and chr(i) or '.' for i in range(256)])  # 1.1


# 1.1 мы создаем строку hexfilter с печатными символами ASCII, если символ непечатный, вместо него выводится точка (.)

# В качестве примера того, что может содержать эта строка, возьмем символьное представление двух целых чисел, 30 и 65,
# в интерактивной оболочке python:

# >>> chr(65)
# 'A'
# >>> chr(30)
# '\x1e'
# >>> len(repr(chr(65)))
# 3
# >>> len(repr(chr(30)))
# 6

# Символьное представление 65 является печатным, а символьное представление 30 - нет. Как видно, представление печатного
# символа имеет длину 3. Воспользуемся этим фактом, чтобы получить итоговую строку HEXFILTER:
# предоставим символ, если это возможно, или точку (.), если нет.

# В списковом включении (list comprehension), с помощью которого создается строка, применяется метод укороченного
# вычисления булевых выражений. Это означает: если длина символа, соответсвующего целому числу в диапазоне 0...255,
# равна 3, мы берем сам символ (chr(i)), а если нет, то точку(.).


def hexdump(src, length=16, show=True):
    if isinstance(src, bytes):  # 1.2
        src = src.decode()

    results = list()
    for i in range(0, len(src), length):
        word = str(src[i:i + length])  # 1.3

        printable = word.translate(HEX_FILTER)  # 1.4
        hexa = ' '.join([f'{ord(c):02X}' for c in word])
        hexwidth = length * 3
        results.append(f'{i:04x} {hexa:<{hexwidth}} {printable}')  # 1.5
    if show:
        for line in results:
            print(line)
    else:
        return results


# Списковое включение позволяет представить первые 256 целых чисел в виде печатных символов. Теперь можно написать
# функцию hexdump. Вначале нужно убедиться в том, что мы получили строку, для этого декодируем строку байтов, если она
# была передана 1.2. Дальше берем часть строки, которую нужно вывести, и присваиваем ее переменной word 1.3. Используем
# встроенную функцию translate, чтобы подставить вместо каждого символа в необработанной строке его строковое
# представление (printable) 1.4. Вместе с тем подставляем шестнадцатеричное представление целочисленного значения для
# каждого символа в исходной строке (hexa). В конце создаем новый массив result для хранения строк, он  будет содержать
# шестнадцатеричное значение индекса первого байта в слове (word), шестнадцатеричное значение слова и его печатное
# представление 1.5. Вывод выглядит так:

# >> hexdump('python rocks\n and proxies roll\n')
# 0000 70 79 74 68 6F 6E 20 72 6F 63 6B 73 0A 20 61 6E  python rocks. an
# 0010 64 20 70 72 6F 78 69 65 73 20 72 6F 6C 6C 0A     d proxies roll.

# Эта функция дает возможность наблюдать за трафиком, проходящим через прокси-сервер, в режиме реального времени.


def receive_from(connection):

    """Мы указываем по умолчанию время ожидания длиной пять секунд 2.1 (при необходимости можно увеличить, поскольку,
     если проксировать трафик в другие страны или по сетям с большими потерями, такое значение может оказаться
     слишком жестким)"""

    buffer = b""
    connection.settimeout(5)  # 2.1
    try:
        while True:
            data = connection.recv(4096)  # 2.2
            if not data:
                break
            buffer += data
    except Exception as e:
        pass
    return buffer


# Для получения как локальных, так и удаленных данных мы передаем объект сокета, который будет использоваться в
# дальнейшем. Создаем пустую байтовую строку buffer, в которой будут накапливаться ответы, полученные из сокета 2.1.
# Подготавливаем цикл, чтобы записывать оветные данные в buffer 2.2, пока они не закончатся или не истечет время
# ожидания. В конце возвращаем байтовую строку buffer вызывающей стороне - ею может быть как локальна, так и удаленная
# система.


# Иногда необходимо модифицировать пакеты запроса или ответа, прежде чем прокси-сервер отправит их по назначению.
# Для этого ниже описаны две функции: request_handler и response_handler.


def request_handler(buffer):
    # модифицируем пакет
    return buffer


def response_handler(buffer):
    # модифицируем пакет
    return buffer


# Внутри этих функций можно изменять содержимое пакетов, заниматься фаззингом, отлаживать проблемы с аутентификацией -
# делать что угодно. Это может пригодиться к примеру, если вы обнаружили передачу учетных данных в открытом виде и
# хотите попробовать повысить свои привелегии в ходе работы с приложением, передав ему admin вместо собственного имени.


def proxy_handler(client_socket, remote_host, remote_port, receive_first):
    remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    remote_socket.connect((remote_host, remote_port))  # 3.1

    if receive_first:  # 3.2
        remote_buffer = receive_from(remote_socket)
        hexdump(remote_buffer)

    remote_buffer = response_handler(remote_buffer)  # 3.3
    if len(remote_buffer):
        print("[<==] Sending %d bytes to localhost." % len(remote_buffer))
        client_socket.send(remote_buffer)

    while True:
        local_buffer = receive_from(client_socket)
        if len(local_buffer):
            line = "[==>]Received %d bytes from localhost." % len(local_buffer)
            print(line)
            hexdump(local_buffer)

            local_buffer = request_handler(local_buffer)
            remote_socket.send(local_buffer)
            print("[==>] Sent to remote.")

        remote_buffer = receive_from(remote_socket)
        if len(remote_buffer):
            print("[<==] Received %d bytes from remote." % len(remote_buffer))
            hexdump(remote_buffer)

            remote_buffer = response_handler(remote_buffer)
            client_socket.send(remote_buffer)
            print("[<==] Sent to localhost.")

        if not len(local_buffer) or not len(remote_buffer):  # 3.4
            client_socket.close()
            remote_socket.close()
            print("[*] No more data. Closing connections.")
            break


# функция proxy_handler содержит основную логику нашего прокси сервера. Для начала мы подключаемся к удаленному
# узлу 3.1. Затем убеждаемся в том, что не нужно инициировать соединение с удаленной стороной и запрашивать данные,
# прежде чем
def server_loop(local_host, local_port, remote_host, remote_port, receive_first):

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # 4.1
    try:
        server.bind((local_host, local_port))  # 4.2
    except Exception as e:
        print('problem on bind: %r' % e)

        print("[!!] Failed to listen on %s:%d" % (local_host, local_port))
        print("[!!] Check for other listening sockets or correct permissions.")
        sys.exit(0)

    print("[*] Listening on %s:%d" % (local_host, local_port))
    server.listen(5)
    while True:  # 4.3
        client_socket, addr = server.accept()
        # выводим информацию о локальном соединении
        line = "> Received incoming connection from %s:%d" % (addr[0], addr[1])
        print(line)
        # создаем поток для взаимодействия с удаленным сервером
        proxy_thread = threading.Thread(
            target=proxy_handler,
            args=(client_socket, remote_host, remote_port, receive_first))  # 4.4
        proxy_thread.start()


"""Функция server_loop создает сокет 4.1, привязывает его к локальному адресу и начинает прослушивать 4.2. В главном 
цикле 4.3, когда приходит запрос на соединение, мы передаем его функции proxy_handler в новом потоке 4.4, которая 
занимается отправкой и приемом битов на том или ином конце потока данных."""


def main():
    if len(sys.argv[1:]) != 5:
        print("Usage: ./proxy.py [localhost] [localport]", end='')
        print("[remotehost] [remoteport] [receive_first]")
        print("Example: ./proxy.py 127.0.0.1 9000 10.12.131.1 9000 True")
        sys.exit(0)
    local_host = sys.argv[1]
    local_port = int(sys.argv[2])
    remote_host = sys.argv[3]
    remote_port = int(sys.argv[4])

    receive_first = sys.argv[5]

    if "True" in receive_first:
        receive_first = True
    else:
        receive_first = False

    server_loop(local_host, local_port, remote_host, remote_port, receive_first)


if __name__ == '__main__':
    main()
