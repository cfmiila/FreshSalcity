import pytest
from app import app, get_db
from database import atualizar_cliente, init_db

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client

def test_tables_exist():
    with app.app_context():
        db = get_db()
        tables = [row['name'] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        for nome in ["usuarios", "clientes", "pecas", "categorias", "vendas", "itens_venda", "trocas"]:
            assert nome in tables

def test_atualizar_cliente_and_relations(client):
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO clientes (nome, whatsapp, email, data_cadastro) VALUES (?, ?, ?, ?)", ('TESTE', '98888-1111', 'exo@ema.il', '2023-01-01'))
        db.commit()
        c = db.execute("SELECT * FROM clientes WHERE email='exo@ema.il'").fetchone()
        atualizar_cliente(c['id'], "TESTEEDIT", "97777-2222", "xx@yy.zz")
        c = db.execute("SELECT * FROM clientes WHERE id=?", (c['id'],)).fetchone()
        assert c['nome'] == "TESTEEDIT"
        assert c['whatsapp'] == "97777-2222"
        assert c['email'] == "xx@yy.zz"

def test_dashboard_route(client):
    with client.session_transaction() as sess:
        sess['usuario_id'] = 1
    response = client.get('/')
    assert response.status_code == 200
    assert b"Dashboard" in response.data

def test_estoque_route(client):
    with client.session_transaction() as sess:
        sess['usuario_id'] = 1
    response = client.get('/estoque')
    assert response.status_code == 200

def test_clientes_route(client):
    with client.session_transaction() as sess:
        sess['usuario_id'] = 1
    response = client.get('/clientes')
    assert response.status_code == 200

def test_vendas_route(client):
    with client.session_transaction() as sess:
        sess['usuario_id'] = 1
    response = client.get('/vendas')
    assert response.status_code == 200

def test_faturamento_venda(client):
    with app.app_context():
        db = get_db()
        cat = db.execute("SELECT id FROM categorias WHERE nome='Calças'").fetchone()
        if not cat:
            db.execute("INSERT INTO categorias (nome) VALUES ('Calças')")
        cat = db.execute("SELECT id FROM categorias WHERE nome='Calças'").fetchone()['id']
        db.execute("INSERT INTO clientes (nome, whatsapp, email, data_cadastro) VALUES (?, ?, ?, ?)", ('FAKE', '95555-0000', 'fat@t.u', '2023-03-02'))
        cli = db.execute("SELECT id FROM clientes WHERE nome='FAKE'").fetchone()['id']
        db.execute("""INSERT INTO pecas (numero_peca, categoria_id, descricao, marca, cor, tamanho, estado_conservacao,
                         preco_custo, preco_venda, status, data_entrada)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, date())""",
                 (9998, cat, 'FakeDesc', 'FakeMark', 'Pretas', 'G', 'Nova', 10.0, 47.0, "vendida"))
        peca = db.execute("SELECT id FROM pecas WHERE numero_peca=9998").fetchone()['id']
        db.execute("INSERT INTO vendas (cliente_id, data_venda, tipo_frete, valor_frete, status_venda) VALUES (?, date(), ?, ?, 'pendente')", (cli, "correios", 10.0))
        venda = db.execute("SELECT id FROM vendas WHERE cliente_id=?", (cli,)).fetchone()['id']
        db.execute("INSERT INTO itens_venda (venda_id, peca_id, preco_vendido) VALUES (?, ?, ?)", (venda, peca, 47.0))
        db.commit()
        total = db.execute("SELECT COALESCE(SUM(preco_venda), 0) AS total FROM pecas WHERE status = 'vendida'").fetchone()['total']
        assert total >= 47.0

def test_formatacao_preco(client):
    with app.app_context():
        db = get_db()
        cat = db.execute("SELECT id FROM categorias WHERE nome='SAPATOS'").fetchone()
        if not cat:
            db.execute("INSERT INTO categorias (nome) VALUES ('SAPATOS')")
        cat = db.execute("SELECT id FROM categorias WHERE nome='SAPATOS'").fetchone()['id']
        db.execute("""INSERT INTO pecas (numero_peca, categoria_id, descricao, marca, cor, tamanho, estado_conservacao,
                         preco_custo, preco_venda, status, data_entrada)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, date())""",
                 (9999, cat, 'FakeShoe', 'Marca', 'Branco', '44', 'Nova', 19.2, 45.0, "vendida"))
        peca = db.execute("SELECT preco_venda FROM pecas WHERE numero_peca=9999").fetchone()['preco_venda']
        assert peca == 45.0