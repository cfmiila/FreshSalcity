# FreshSalCity — Gestão Integrada de Brechó e Moda Circular

Sistema completo para brechós, moda circular e projetos de economia colaborativa: gere clientes, estoque de peças, vendas, desapegos da comunidade, moderação e Vitrine Pública em um só lugar.

---

## Principais Funcionalidades

- **Painel Administrativo**
  - Gestão de estoque de peças (CRUD)
  - Controle de vendas (inclui gestão de clientes, atualização automática de históricos/totais, status de envio/frete)
  - CRM de clientes: cadastro, busca, histórico dinâmico de compras, gasto total, última compra
  - Relatórios gerenciais (faturamento, peças paradas, BI)

- **Comunidade & Desapego Colaborativo**
  - Formulário público para envio fácil de peças da comunidade
  - Moderação/administração de desapegos: aprovar, recusar, editar descrição, preço, categoria
  - Aprovação automática publica a peça na Vitrine Circular

- **Vitrine Circular Pública**
  - Catálogo online de peças disponíveis (apenas status 'disponivel')
  - Busca e filtro por categoria
  - Visual amigável, responsivo e com identidade visual FreshSalCity

---

## Arquitetura & Tecnologias
- **Backend**: Python 3, Flask, SQLite3, Jinja2 Templates
- **Frontend**: HTML5, CSS3 responsivo, paleta rosa neon exclusiva, grid/flexbox
- **Banco**: único arquivo SQLite (`freshsalcity.db`)
- **Uploads**: imagens em `static/uploads/` ou `static/fotos/`

---

## Como Executar Localmente

1. (Recomendado) Crie e ative um ambiente virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate    # Windows
   ```
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Inicialize as tabelas (apenas na 1ª vez):
   ```bash
   python database.py
   ```
4. Execute o servidor:
   ```bash
   python app.py
   ```
5. Acesse em `http://localhost:5000`

---

## Estrutura de Pastas

```
├── app.py               # Lógica principal, rotas e servidor Flask
├── database.py          # Criação e manipulação do banco SQLite
├── requirements.txt     # Dependências PyPI
├── static/
│   ├── style.css
│   ├── logo.png
│   └── uploads/         # Imagens dos desapegos/comunidade
│   └── fotos/           # Fotos de peças do brechó
├── templates/           # Templates Jinja2 (HTML)
│   ├── base.html
│   ├── dashboard.html
│   ├── clientes.html
│   ├── estoque.html
│   ├── vendas.html
│   ├── relatorios.html
│   ├── vitrine.html
│   ├── desapegar_form.html
│   └── ...
├── freshsalcity.db      # Banco de dados SQLite (aparece só após rodar)
```

---

## Contribuição

Contribuições são bem-vindas! Veja o código, adapte para o seu brechó, faça forks e envie melhorias via Pull Request.

---

Projeto desenvolvido por Fresh SalCity — Moda Circular & Sustentável
