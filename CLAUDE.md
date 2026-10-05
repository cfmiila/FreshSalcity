# Fresh SalCity — Sistema de Gestão de Estoque

## Sobre o projeto
Sistema web interno para o brechó Fresh SalCity (Salvador, BA).
Substitui planilhas Excel pelo controle digital de estoque, clientes, vendas e relatórios.
Desenvolvido como projeto de extensão universitária em moda sustentável.

## Stack
- Backend: Python + Flask
- Banco: SQLite (arquivo freshsalcity.db)
- Frontend: HTML + CSS + Jinja2 (sem frameworks JS)
- PDF: WeasyPrint
- Deploy: Railway

## Estrutura do projeto
```
freshsalcity/
├── app.py              # servidor Flask, todas as rotas
├── database.py         # cria e acessa o SQLite
├── requirements.txt
├── Procfile            # instrução para o Railway
├── .env                # variáveis de ambiente (não vai pro GitHub)
├── CLAUDE.md           # este arquivo
├── migrations/         # scripts de alteração do banco
├── static/
│   ├── style.css
│   └── fotos/          # fotos das peças (não vão pro GitHub)
└── templates/
    ├── base.html
    ├── dashboard.html
    ├── estoque.html
    ├── peca_form.html
    ├── clientes.html
    ├── cliente_form.html
    ├── vendas.html
    ├── venda_form.html
    ├── troca_form.html
    ├── relatorios.html
    └── relatorio_pdf.html
```

## Banco de dados
7 tabelas: usuarios, categorias, pecas, clientes, vendas, itens_venda, trocas.
Rodar uma vez para criar: `python database.py`
Alterações no banco sempre via migrations em /migrations/.

## Identidade visual
- Rosa neon: #FF2D9B
- Preto: #1A1A1A
- Fundo: #F5F4F0
- Fonte: DM Sans (Google Fonts)
- Elemento gráfico: xadrez preto e branco
- Wave bar: gradiente rosa → lilás → verde-água no topo de cada tela

## Módulos do sistema
1. Autenticação — login com email e senha (bcrypt)
2. Estoque — CRUD de peças, número automático, status por cor, alerta +60 dias, foto da peça
3. Clientes — cadastro, histórico de compras, ticket médio automático
4. Vendas — múltiplas peças por venda, frete (Correios ou taxa fixa SSA), margem automática
5. Trocas — validação de 7 dias corridos
6. Relatórios — BI com exportação em PDF (WeasyPrint)

## Status das peças
- disponivel → branco
- curadoria  → amarelo
- desconto   → laranja (peças +60 dias paradas)
- perda      → vermelho
- vendida    → verde (badge rosa no sistema)

## Regras de negócio importantes
- Número da peça gerado automaticamente (MAX + 1), igual à planilha Excel atual
- Troca permitida em até 7 dias corridos em bom estado
- Frete: Correios (valor digitado) ou entrega local SSA (taxa fixa — confirmar valor com cliente)
- Alerta automático para peças disponíveis há mais de 60 dias
- Tamanho usa numeração (36, 38, 40...) — confirmado com a cliente
- Sistema de uso individual (somente a proprietária)

## Pontos ainda a confirmar com a cliente
- Valor fixo da taxa de entrega local em SSA
- Lista completa de categorias que ela usa hoje
- Prazo exato do alerta de peças paradas (sugestão: 60 dias)

## Convenções de código
- Rotas em português (ex: /estoque, /clientes, /vendas)
- Nomes de variáveis em português (ex: peca, cliente, venda)
- Templates herdam sempre de base.html via {% extends %}
- Banco acessado via get_db() do database.py
- Senhas sempre com bcrypt, nunca texto puro
- Variáveis sensíveis sempre no .env, nunca hardcoded

## Como rodar localmente
```
venv\Scripts\activate          # Windows
source venv/bin/activate       # Mac/Linux
pip install -r requirements.txt
python database.py
python app.py
# acesse: http://localhost:5000
```

## Commits
Padrão: `fase N: descrição do que foi feito`
