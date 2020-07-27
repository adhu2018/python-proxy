# -*- coding: cp1252 -*-
# <PythonProxy.py>
#
#Copyright (c) <2009> <Fábio Domingues - fnds3000 in gmail.com>
#
#Permission is hereby granted, free of charge, to any person
#obtaining a copy of this software and associated documentation
#files (the "Software"), to deal in the Software without
#restriction, including without limitation the rights to use,
#copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the
#Software is furnished to do so, subject to the following
#conditions:
#
#The above copyright notice and this permission notice shall be
#included in all copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
#OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
#NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
#WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#OTHER DEALINGS IN THE SOFTWARE.

"""\
Copyright (c) <2009> <Fábio Domingues - fnds3000 in gmail.com> <MIT Licence>

                  **************************************
                 *** Python Proxy - A Fast HTTP proxy ***
                  **************************************

Neste momento este proxy é um Elie Proxy.

Suporta os métodos HTTP:
 - OPTIONS;
 - GET;
 - HEAD;
 - POST;
 - PUT;
 - DELETE;
 - TRACE;
 - CONENCT.

Suporta:
 - Conexões dos cliente em IPv4 ou IPv6;
 - Conexões ao alvo em IPv4 e IPv6;
 - Conexões todo o tipo de transmissão de dados TCP (CONNECT tunneling),
     p.e. ligações SSL, como é o caso do HTTPS.

A fazer:
 - Verificar se o input vindo do cliente está correcto;
   - Enviar os devidos HTTP erros se não, ou simplesmente quebrar a ligação;
 - Criar um gestor de erros;
 - Criar ficheiro log de erros;
 - Colocar excepções nos sítios onde é previsível a ocorrência de erros,
     p.e.sockets e ficheiros;
 - Rever tudo e melhorar a estrutura do programar e colocar nomes adequados nas
     variáveis e métodos;
 - Comentar o programa decentemente;
 - Doc Strings.

Funcionalidades futuras:
 - Adiconar a funcionalidade de proxy anónimo e transparente;
 - Suportar FTP?.


(!) Atenção o que se segue só tem efeito em conexões não CONNECT, para estas o
 proxy é sempre Elite.

Qual a diferença entre um proxy Elite, Anónimo e Transparente?
 - Um proxy elite é totalmente anónimo, o servidor que o recebe não consegue ter
     conhecimento da existência do proxy e não recebe o endereço IP do cliente;
 - Quando é usado um proxy anónimo o servidor sabe que o cliente está a usar um
     proxy mas não sabe o endereço IP do cliente;
     É enviado o cabeçalho HTTP "Proxy-agent".
 - Um proxy transparente fornece ao servidor o IP do cliente e um informação que
     se está a usar um proxy.
     São enviados os cabeçalhos HTTP "Proxy-agent" e "HTTP_X_FORWARDED_FOR".

"""

import _thread as thread
import re
import socket, select
try:
    from tools import filter_, api_parse
except ImportError:
    pass
except ModuleNotFoundError:
    pass

__version__ = "0.1.1"
BUFLEN = 8192
VERSION = "Python Proxy/" + __version__
HTTPVER = "HTTP/1.1"

class ConnectionHandler:
    def __init__(self, connection, address, timeout):
        self.client = connection
        self.client_buffer = ""
        self.timeout = timeout
        self.method, self.path, self.protocol = self.get_base_header()
        try:
            self.path = filter_(self.path)
        except NameError:
            pass
        if not self.path:
            return
        elif self.api_():
            self.api()
        elif self.method=="CONNECT":
            self.method_CONNECT()
        elif self.method in ("OPTIONS", "GET", "HEAD", "POST", "PUT",
                             "DELETE", "TRACE"):
            self.method_others()
        self.client.close()
        try:
            self.target.close()
        except AttributeError:
            pass
    
    def api_(self):
        if re.search(r"mumuceo\.com", self.path) and re.search(r"^http:", self.path):
            return True
        elif re.search(r"^/", self.path):
            print("Use a custom api.", self.path)
            return True
        else:
            return False
    
    def api(self):
        # default
        status = 200
        headers = [("Content-Type", "text/html;charset=utf-8")]
        if re.search(r"mumuceo\.com", self.path) and re.search(r"^http:", self.path):  # 
            self.path = re.sub(r"^http:", r"https:", self.path)
            data = """
                <script language="javascript" type="text/javascript">
                    window.location.href="{}";
                </script>
                """.format(self.path)
        else:
            try:
                data = api_parse.main(self.path)
            except NameError:
                # You can customize a module that returns a value type of str to parse the api.
                # Access the custom api in the browser via address (http://xxx.xxx.xxx.xxx:8080/aaa).
                # self.path => "/aaa"
                data = "The module used to resolve the api could not be found."
        self.apisend(status, headers, data)

    def set_header(self, status, headers):
        # default
        respond_header = "HTTP/1.1 {} \r\n".format(status)
        for i in headers:
            respond_header += "{}:{}\r\n".format(i[0], i[1])
        respond_header += "\r\n"
        return respond_header
    
    def apisend(self, status, headers, data):
        respond_header = self.set_header(status, headers)
        respond = respond_header + data
        self.client.send(respond.encode())
        self.client_buffer = ""

    def get_base_header(self):
        while 1:
            self.client_buffer += self.client.recv(BUFLEN).decode("utf8","ignore")
            end = self.client_buffer.find("\n")
            if end != -1:
                break
        print(self.client_buffer[:end])
        data = (self.client_buffer[:end+1]).split()
        self.client_buffer = self.client_buffer[end+1:]
        return data

    def method_CONNECT(self):
        self._connect_target(self.path)
        self.client.send((HTTPVER + " 200 Connection established\n" +
                         "Proxy-agent: %s\n\n" % VERSION).encode())
        self.client_buffer = ""
        self._read_write()

    def method_others(self):
        self.path = self.path[7:]
        i = self.path.find("/")
        host = self.path[:i]        
        path = self.path[i:]
        self._connect_target(host)
        temp = "{} {} {}\n".format(self.method, path, self.protocol) + self.client_buffer
        # print("\n"+temp)  # debug
        self.target.send(temp.encode())
        self.client_buffer = ""
        self._read_write()

    def _connect_target(self, host):
        i = host.find(":")
        if i != -1:
            port = int(host[i+1:])
            host = host[:i]
        else:
            port = 80
        (soc_family, _, _, _, address) = socket.getaddrinfo(host, port)[0]
        self.target = socket.socket(soc_family)
        try:
            self.target.connect(address)
        except ConnectionRefusedError:
            print("ConnectionRefusedError.")
        except TimeoutError:
            print("TimeoutError.")
            pass

    def _read_write(self):
        time_out_max = self.timeout / 3
        socs = [self.client, self.target]
        count = 0
        while 1:
            count += 1
            (recv, _, error) = select.select(socs, [], socs, 3)
            if error:
                break
            if recv:
                for in_ in recv:
                    data = in_.recv(BUFLEN)
                    if in_ is self.client:
                        out = self.target
                    else:
                        out = self.client
                    if data:
                        out.send(data)
                        count = 0
            if count == time_out_max:
                break

def start_server(host="0.0.0.0", port=8080, IPv6=False, timeout=60,
                  handler=ConnectionHandler):
    if IPv6 == True:
        soc_type = socket.AF_INET6
    else:
        soc_type = socket.AF_INET
    soc = socket.socket(soc_type)
    soc.bind((host, port))
    print("Serving on {}:{}.".format(host, port))
    soc.listen(0)
    while 1:
        thread.start_new_thread(handler, soc.accept()+(timeout,))

if __name__ == "__main__":
    start_server()
