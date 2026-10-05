# Exemplo de migration — copie este arquivo, renomeie e adapte
# Nunca edite uma migration já executada
# Rode: python migrations/nome_do_arquivo.py

import sqlite3

conn = sqlite3.connect('freshsalcity.db')

# Exemplo: adicionar nova categoria
# conn.execute("INSERT OR IGNORE INTO categorias (nome) VALUES ('Shorts')")

# Exemplo: adicionar nova coluna
# conn.execute("ALTER TABLE pecas ADD COLUMN nova_coluna TEXT")

conn.commit()
conn.close()
print("Migration executada!")
