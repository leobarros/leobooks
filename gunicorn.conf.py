"""Configuração do Gunicorn para o container.

O access log HTTP é emitido pela aplicação em JSON (incluindo request_id,
duração e status). O Docker não habilita o access log tradicional do Gunicorn
para não duplicar cada requisição; erros do servidor continuam no error log.
"""

from gunicorn.glogging import Logger


class LeoBooksLogger(Logger):
    def access(self, resp, req, environ, request_time):
        if environ.get("PATH_INFO") == "/healthz":
            return
        super().access(resp, req, environ, request_time)


logger_class = LeoBooksLogger
