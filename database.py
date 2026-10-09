import sqlite3
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()


def get_db():
    conn = sqlite3.connect('freshsalcity.db')
    # Ativa o suporte a Foreign Keys no SQLite
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript('''

        CREATE TABLE IF NOT EXISTS usuarios (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            nome  TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS categorias (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS pecas (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_peca        INTEGER UNIQUE NOT NULL,
            categoria_id       INTEGER NOT NULL,
            descricao          TEXT,
            marca              TEXT NOT NULL,
            cor                TEXT NOT NULL,
            tamanho            TEXT NOT NULL,
            estado_conservacao TEXT NOT NULL,
            preco_custo        REAL NOT NULL,
            preco_venda        REAL NOT NULL,
            status             TEXT NOT NULL DEFAULT 'disponivel',
            foto               TEXT,
            observacoes        TEXT,
            data_entrada       DATE NOT NULL,
            data_venda         DATE,
            FOREIGN KEY (categoria_id) REFERENCES categorias(id)
        );

        CREATE TABLE IF NOT EXISTS clientes (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            nome          TEXT NOT NULL,
            whatsapp      TEXT NOT NULL,
            email         TEXT,
            instagram     TEXT,
            data_cadastro DATE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS vendas (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id   INTEGER,
            data_venda   DATE NOT NULL,
            tipo_frete   TEXT NOT NULL,
            valor_frete  REAL NOT NULL DEFAULT 0,
            status_venda TEXT NOT NULL DEFAULT 'pendente',
            observacoes  TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        );

        CREATE TABLE IF NOT EXISTS itens_venda (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id      INTEGER NOT NULL,
            peca_id       INTEGER NOT NULL,
            preco_vendido REAL NOT NULL,
            FOREIGN KEY (venda_id) REFERENCES vendas(id),
            FOREIGN KEY (peca_id)  REFERENCES pecas(id)
        );

        CREATE TABLE IF NOT EXISTS trocas (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            item_venda_id   INTEGER NOT NULL,
            data_devolucao  DATE NOT NULL,
            peca_nova_id    INTEGER,
            diferenca_valor REAL DEFAULT 0,
            observacoes     TEXT,
            FOREIGN KEY (item_venda_id) REFERENCES itens_venda(id),
            FOREIGN KEY (peca_nova_id)  REFERENCES pecas(id)
        );

        INSERT OR IGNORE INTO categorias (nome) VALUES
            ('Vestidos'),
            ('Blusas'),
            ('Calças'),
            ('Saias'),
            ('Casacos'),
            ('Sapatos'),
            ('Acessórios'),
            ('Bermuda/Shorts'),
            ('Outros');

    ''')

    email = os.getenv('ADMIN_EMAIL', 'admin@freshsalcity.com')
    senha = os.getenv('ADMIN_SENHA', 'fresh2026').encode()
    senha_hash = bcrypt.hashpw(senha, bcrypt.gensalt()).decode()
    c.execute(
        "INSERT OR IGNORE INTO usuarios (nome, email, senha) VALUES (?,?,?)",
        ('Fresh Sal City', email, senha_hash)
    )

    # --- ÁREA PÚBLICA, MODA CIRCULAR, 3C ---
    c.execute('''
    CREATE TABLE IF NOT EXISTS desapegos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_nome TEXT,
        cliente_whatsapp TEXT,
        cliente_instagram TEXT,
        descricao TEXT,
        categoria_id INTEGER,
        tamanho TEXT,
        estado_conservacao TEXT,
        preco_sugerido REAL,
        tipo_intent TEXT CHECK(tipo_intent IN ('venda','doacao')) DEFAULT 'doacao',
        foto TEXT,
        status TEXT CHECK(status IN ('em_analise','aprovado','recusado')) DEFAULT 'em_analise',
        data_envio DATE DEFAULT CURRENT_DATE,
        FOREIGN KEY (categoria_id) REFERENCES categorias(id)
    );
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS comentarios_pecas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        peca_id INTEGER,
        autor_nome TEXT,
        autor_contato TEXT,
        mensagem TEXT,
        resposta_admin TEXT,
        data_criacao DATE DEFAULT CURRENT_DATE,
        FOREIGN KEY (peca_id) REFERENCES pecas(id)
    );
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS reservas_pecas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        peca_id INTEGER,
        cliente_nome TEXT,
        cliente_whatsapp TEXT,
        status TEXT CHECK(status IN ('pendente','confirmada','cancelada')) DEFAULT 'pendente',
        data_reserva DATE DEFAULT CURRENT_DATE,
        FOREIGN KEY (peca_id) REFERENCES pecas(id)
    );
    ''')
    conn.commit()
    conn.close()
    print("Banco criado com sucesso!")


def atualizar_cliente(id, nome, whatsapp, email):
    conn = get_db()
    conn.execute(
        "UPDATE clientes SET nome = ?, whatsapp = ?, email = ? WHERE id = ?",
        (nome, whatsapp, email, id)
    )
    conn.commit()
    conn.close()


def migrar_db():
    """Remove categorias duplicadas e reatribui as peças para as categorias acentuadas."""
    conn = get_db()
    c = conn.cursor()

    
    correcoes = [
        ('Calcas', 'Calças'),
        ('Acessorios', 'Acessórios')
    ]

    for antiga, nova in correcoes:
       
        c.execute("SELECT id FROM categorias WHERE nome = ?", (antiga,))
        res_antiga = c.fetchone()
        
        c.execute("SELECT id FROM categorias WHERE nome = ?", (nova,))
        res_nova = c.fetchone()

        if res_antiga and res_nova:
            id_antigo = res_antiga['id']
            id_novo = res_nova['id']
            c.execute("UPDATE pecas SET categoria_id = ? WHERE categoria_id = ?", (id_novo, id_antigo))
            
            c.execute("DELETE FROM categorias WHERE id = ?", (id_antigo,))

        elif res_antiga and not res_nova:
            
            c.execute("UPDATE categorias SET nome = ? WHERE id = ?", (nova, res_antiga['id']))

    # Remove as categorias extras, mantendo apenas as desejadas
    categorias_desejadas = ['Calças', 'Saias', 'Acessórios', 'Blusas', 'Casacos']
    c.execute("SELECT id, nome FROM categorias")
    for row in c.fetchall():
        if row['nome'] not in categorias_desejadas:
            # Reatribua peças com categoria que será removida para NULL ou uma categoria padrão, se desejado
            c.execute("UPDATE pecas SET categoria_id = NULL WHERE categoria_id = ?", (row['id'],))
            c.execute("DELETE FROM categorias WHERE id = ?", (row['id'],))
    conn.commit()
    conn.close()
    print("Limpeza de duplicadas realizada com sucesso!")


def atualizar_venda(venda_id, cliente_id, data_venda, tipo_frete, valor_frete, status_venda, observacoes):
    conn = get_db()
    conn.execute(
        "UPDATE vendas SET cliente_id=?, data_venda=?, tipo_frete=?, valor_frete=?, status_venda=?, observacoes=? WHERE id=?",
        (cliente_id, data_venda, tipo_frete, valor_frete, status_venda, observacoes, venda_id)
    )
    conn.commit()
    conn.close()
    
def buscar_venda_por_id(venda_id):
    """Busca uma venda específica pelo ID."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM vendas WHERE id = ?", (venda_id,))
    venda = c.fetchone()
    conn.close()
    return venda

def deletar_cliente(id):
    conn = get_db()
    conn.execute("UPDATE vendas SET cliente_id = NULL WHERE cliente_id = ?", (id,))
    conn.execute("DELETE FROM clientes WHERE id = ?", (id,))
    conn.commit()
    conn.close()

def deletar_peca(id):
    conn = get_db()
    conn.execute("DELETE FROM pecas WHERE id = ?", (id,))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    migrar_db()