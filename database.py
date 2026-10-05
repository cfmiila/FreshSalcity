import sqlite3
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()


def get_db():
    conn = sqlite3.connect('freshsalcity.db')
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
            ('Calcas'),
            ('Saias'),
            ('Casacos'),
            ('Sapatos'),
            ('Acessorios'),
            ('Outros');

    ''')

    email = os.getenv('ADMIN_EMAIL', 'admin@freshsalcity.com')
    senha = os.getenv('ADMIN_SENHA', 'fresh2026').encode()
    senha_hash = bcrypt.hashpw(senha, bcrypt.gensalt()).decode()
    c.execute(
        "INSERT OR IGNORE INTO usuarios (nome, email, senha) VALUES (?,?,?)",
        ('Fresh Sal City', email, senha_hash)
    )

    conn.commit()
    conn.close()
    print("Banco criado com sucesso!")


if __name__ == '__main__':
    init_db()
