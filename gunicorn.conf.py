"""Configuração do Gunicorn para o container.

O endpoint /healthz é chamado pelo Docker a cada 5 minutos. Ele não representa
uma ação de usuário e não deve poluir o access log; erros do próprio health
continuam visíveis no log de erro do container.
"""

from gunicorn.glogging import Logger


class LeoBooksLogger(Logger):
    def access(self, resp, req, environ, request_time):
        if environ.get("PATH_INFO") == "/healthz":
            return
        super().access(resp, req, environ, request_time)


logger_class = LeoBooksLogger
