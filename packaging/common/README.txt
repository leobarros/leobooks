LeoBooks — instalação nativa
============================

Código:       /opt/leobooks/app
Ambiente:     /opt/leobooks/venv
Configuração: /etc/leobooks/leobooks.env
Dados:        /var/lib/leobooks
Serviço:      systemd leobooks.service
Porta:        5057

Editar a configuração:
  sudo nano /etc/leobooks/leobooks.env
  sudo systemctl restart leobooks

Abrir:
  http://127.0.0.1:5057

Logs:
  journalctl -u leobooks -f

Dados persistentes:
  /var/lib/leobooks/leobooks.db
  /var/lib/leobooks/covers/
  /var/lib/leobooks/uploads/
  /var/lib/leobooks/backups/

Backup/restore completo: Ajustes → Dados e backup.
