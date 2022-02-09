#  В python UDP-клиент мало отличается от TCP-клиента, нам нужно внести всего два небольших изменения, чтобы он мог
# отправлять пакеты в формате UDP.

import socket

target_host = "127.0.0.1"
target_port = 9997

# создаем объект сокета
client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # 1

# отправляем какие-нибудь данные
client.sendto(b"AAABBBCCC", (target_host, target_port))  # 2

# принимаем какие-нибудь данные
data, addr = client.recvfrom(4096)  # 3

print(data.decode())
client.close()
