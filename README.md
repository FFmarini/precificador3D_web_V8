# Precificador 3D Web V8

> Aviso de licenca:
> Este projeto esta sob licenca restritiva.
> O uso e permitido apenas para fins pessoais, internos ou de avaliacao.
> Nao e permitido vender, modificar ou redistribuir sem autorizacao expressa.

Aplicacao web em Flask para orcamento, gestao de pedidos e operacao de uma pequena producao de impressao 3D.

Se o app te ajudou e quiser me ajudar, segue o Pix. Agradeco o incentivo para futuras versoes.

Duvidas e sugestoes: coffeedev34@gmail.com

Chave Pix: `1f43dfb3-ad0d-4874-b2fb-c3604de4733d`

<img width="169" height="169" alt="QR code Pix" src="https://github.com/user-attachments/assets/12bc90d8-3d5f-4235-bf32-aa8c11e0e5f0" />

## Principais recursos

- Cadastro de clientes, projetos, filamentos e pedidos
- Precificacao com base em tempo de impressao, consumo de material, energia e margem
- Separacao operacional por abas:
  - `Pedidos`
  - `Estoque`
  - `Historico`
- Campo `Pago` nos pedidos
- Busca e ordenacao nas listagens principais
- Geracao de PDF por pedido
- Recibo consolidado por cliente
- Controle de estoque de filamento em gramas
- Movimentacoes de estoque
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
2. Instale as dependencias:

```bash
pip install -r requirements.txt
```

3. Execute a aplicacao:

```bash
python web_app.py
```

4. Abra no navegador:

```text
http://127.0.0.1:5000
```

## Banco de dados

Por padrao, em ambiente Linux de deploy o banco fica em:

```text
/opt/precificador/data/precificador.db
```

O caminho tambem pode ser definido pela variavel de ambiente:

```text
PREC_DB_PATH
```

## Deploy rapido em Debian/Ubuntu/CT Proxmox

1. Envie os arquivos do projeto.
2. Entre na pasta do projeto.
3. Rode:

```bash
sudo bash scripts/install_on_debian.sh
```

Comandos uteis:

```bash
systemctl status precificador --no-pager
journalctl -u precificador -f
```

## Observacoes de versionamento

O repositorio ignora arquivos sensiveis ou gerados localmente, como:

- bancos `.db`
- PDFs gerados
- uploads
- backups
- arquivos temporarios

## Licenca

Este projeto utiliza uma licenca restritiva de uso.

Em resumo:

- o uso e permitido apenas para fins pessoais, internos ou de avaliacao;
- nao e permitido vender, revender ou usar comercialmente sem autorizacao;
- nao e permitido modificar ou redistribuir o codigo sem autorizacao expressa.

Leia o arquivo `LICENSE` para o texto completo.

## Status atual da V8

Nesta versao, o projeto ja inclui:

- V8 publicada e validada em producao
- migracoes de banco para novos campos da V8
- suporte a homologacao com HTTPS interno
- certificados internos de exemplo nos scripts de deploy

## Proximos passos sugeridos

Screenshot
<img width="1893" height="1020" alt="image" src="https://github.com/user-attachments/assets/1d7523c9-b9e9-4ffd-a53b-9271bc1bd5cc" />
<img width="1901" height="1033" alt="image" src="https://github.com/user-attachments/assets/fbfcddf4-e6f2-4b3b-a50e-5f5c282c5fab" />
<img width="1601" height="467" alt="image" src="https://github.com/user-attachments/assets/58bd622b-30f0-438e-b0e6-6e378f379849" />
<img width="1919" height="587" alt="image" src="https://github.com/user-attachments/assets/6bad2ac3-23d7-470a-a18c-41e1d7923dc7" />
<img width="1893" height="565" alt="image" src="https://github.com/user-attachments/assets/2096863c-5afa-4390-815b-7bb892c70faf" />
<img width="1915" height="592" alt="image" src="https://github.com/user-attachments/assets/aed4aa07-5f73-4edd-9546-36e63f94b153" />
<img width="1911" height="1035" alt="image" src="https://github.com/user-attachments/assets/9533433e-4413-49cb-95e4-ae29f735bca3" />






- melhorar extracao automatica de miniaturas de projetos a partir de paginas web
- separar configuracao de homologacao e producao por variaveis de ambiente
- adicionar documentacao de backup e restauracao
- criar changelog por versao
