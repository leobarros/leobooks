LeoBooks — instalação nativa
============================

Código:       /opt/leobooks/app
Ambiente:     /opt/leobooks/venv
Configuração: /etc/leobooks/leobooks.env
Dados:        /var/lib/leobooks
Aplicativo:   leobooks (GTK/WebKit, sem navegador externo)
Serviço:      systemd leobooks.service
Porta:        5057

Editar a configuração:
  sudo nano /etc/leobooks/leobooks.env
  sudo systemctl restart leobooks

Abrir:
  menu LeoBooks ou execute: leobooks
  (a interface roda em uma janela GTK; o serviço local usa a porta 5057)

Logs:
  journalctl -u leobooks -f

Dados persistentes:
  /var/lib/leobooks/leobooks.db
  /var/lib/leobooks/covers/
  /var/lib/leobooks/uploads/
  /var/lib/leobooks/backups/

Backup/restore completo: Ajustes → Dados e backup.
