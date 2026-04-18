Deploy rápido no Debian/Ubuntu/CT Proxmox

1) Envie e extraia o zip
2) Entre na pasta extraída
3) Rode:
   sudo bash scripts/install_on_debian.sh

Banco:
- O SQLite fica em /opt/precificador/data/precificador.db

Service:
- systemctl status precificador --no-pager
- journalctl -u precificador -f
