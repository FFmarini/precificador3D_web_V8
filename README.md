# Precificador 3D Web V8

Aplicação web em Flask para orçamento, gestão de pedidos e operação de uma pequena produção de impressão 3D.
Se o App te ajudou e quiser me ajudar segue o pix, agradeço o incentivo para futuras versões.
Dúvidas e sugestões - coffeedev34@gmail.com

Chave Pix - 1f43dfb3-ad0d-4874-b2fb-c3604de4733d
<img width="169" height="169" alt="image" src="https://github.com/user-attachments/assets/12bc90d8-3d5f-4235-bf32-aa8c11e0e5f0" />


## Principais recursos

- Cadastro de clientes, projetos, filamentos e pedidos
- Precificação com base em tempo de impressão, consumo de material, energia e margem
- Separação operacional por abas:
  - `Pedidos`
  - `Estoque`
  - `Histórico`
- Campo `Pago` nos pedidos
- Busca e ordenação nas listagens principais
- Geração de PDF por pedido
- Recibo consolidado por cliente
- Controle de estoque de filamento em gramas
- Movimentações de estoque
- HTTPS interno para uso em rede privada/ZeroTier
- Miniatura opcional para projetos por URL de imagem

## Stack

- Python 3
- Flask
- Gunicorn
- SQLite
- ReportLab

## Estrutura do projeto

```text
app/
  db.py
  pdfs.py
  pricing.py
scripts/
templates/
static/
web_app.py
precificador.service
requirements.txt
```

## Como rodar localmente

1. Crie e ative um ambiente virtual.
2. Instale as dependências:

```bash
pip install -r requirements.txt
```

3. Execute a aplicação:

```bash
python web_app.py
```

4. Abra no navegador:

```text
http://127.0.0.1:5000
```

## Banco de dados

Por padrão, em ambiente Linux de deploy o banco fica em:

```text
/opt/precificador/data/precificador.db
```

O caminho também pode ser definido pela variável de ambiente:

```text
PREC_DB_PATH
```

## Deploy rápido em Debian/Ubuntu/CT Proxmox

1. Envie os arquivos do projeto.
2. Entre na pasta do projeto.
3. Rode:

```bash
sudo bash scripts/install_on_debian.sh
```

Comandos úteis:

```bash
systemctl status precificador --no-pager
journalctl -u precificador -f
```

## Observações de versionamento

O repositório ignora arquivos sensíveis ou gerados localmente, como:

- bancos `.db`
- PDFs gerados
- uploads
- backups
- arquivos temporários

## Licença

Este projeto utiliza uma licença restritiva de uso.

Em resumo:

- o uso é permitido apenas para fins pessoais, internos ou de avaliação;
- não é permitido vender, revender ou usar comercialmente sem autorização;
- não é permitido modificar ou redistribuir o código sem autorização expressa.

Leia o arquivo `LICENSE` para o texto completo.

## Status atual da V8

Nesta versão, o projeto já inclui:

- V8 publicada e validada em produção
- migrações de banco para novos campos da V8
- suporte a homologação com HTTPS interno
- certificados internos de exemplo nos scripts de deploy

## Próximos passos sugeridos

- melhorar extração automática de miniaturas de projetos a partir de páginas web
- separar configuração de homologação e produção por variáveis de ambiente
- adicionar documentação de backup e restauração
- criar changelog por versão

Screeshots
<img width="1598" height="1032" alt="image" src="https://github.com/user-attachments/assets/6d8e523f-4794-48d3-ac0f-c6aca507c92e" />
<img width="1731" height="1024" alt="image" src="https://github.com/user-attachments/assets/b7dcc129-8384-4dcf-a6b5-986a816b4012" />
<img width="1901" height="1031" alt="image" src="https://github.com/user-attachments/assets/1087cd69-9b2c-4d13-9042-0057e86842bf" />



