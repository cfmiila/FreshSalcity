import os
import sqlite3
from datetime import date, datetime
from functools import wraps
from io import BytesIO

import bcrypt
from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

try:
    from weasyprint import HTML
except (ImportError, OSError):
    HTML = None

from database import init_db

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'freshsalcity-secret-dev')
app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'fotos')
app.config['DATABASE'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'freshsalcity.db')
app.config['TAXA_LOCAL_SSA'] = os.getenv('TAXA_LOCAL_SSA', '30')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def get_db():
    if 'db' not in g:
        conn = sqlite3.connect(app.config['DATABASE'])
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get('usuario_id'):
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return wrapper


def salvar_foto(arquivo):
    if not arquivo or not arquivo.filename:
        return None
    nome_seguro = secure_filename(arquivo.filename)
    extensao = os.path.splitext(nome_seguro)[1].lower()
    if extensao not in {'.png', '.jpg', '.jpeg', '.webp'}:
        return None
    nome_arquivo = f"{int(datetime.now().timestamp())}{extensao}"
    caminho = os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo)
    arquivo.save(caminho)
    return f'/static/fotos/{nome_arquivo}'


def numero_peca_automatico(db):
    ultimo = db.execute('SELECT COALESCE(MAX(numero_peca), 0) FROM pecas').fetchone()[0]
    return int(ultimo) + 1


def calcular_dias(data_text):
    if not data_text:
        return 0
    try:
        return (date.today() - datetime.strptime(data_text, '%Y-%m-%d').date()).days
    except ValueError:
        return 0


def formatar_moeda(valor):
    valor = float(valor or 0)
    return f'R$ {valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def valor_decimal(valor, padrao=0.0):
    try:
        texto = str(valor or '').strip().replace('R$', '').replace('.', '').replace(',', '.')
        return float(texto) if texto else padrao
    except (TypeError, ValueError):
        return padrao


def status_badge(status):
    mapeamento = {
        'disponivel': 'b-disponivel',
        'curadoria': 'b-curadoria',
        'desconto': 'b-desconto',
        'perda': 'b-perda',
        'vendida': 'b-vendida',
    }
    return mapeamento.get(status, 'b-disponivel')


app.jinja_env.globals['status_badge'] = status_badge
app.jinja_env.filters['moeda'] = formatar_moeda


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('usuario_id'):
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        senha = request.form.get('senha', '')
        db = get_db()
        usuario = db.execute('SELECT * FROM usuarios WHERE email = ?', (email,)).fetchone()

        if usuario and bcrypt.checkpw(senha.encode('utf-8'), usuario['senha'].encode('utf-8')):
            session.clear()
            session['usuario_id'] = usuario['id']
            session['usuario_nome'] = usuario['nome']
            return redirect(url_for('dashboard'))

        flash('Email ou senha inválidos.', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def dashboard():
    db = get_db()

    total_pecas = db.execute('SELECT COUNT(*) AS total FROM pecas').fetchone()['total']
    total_disponiveis = db.execute("SELECT COUNT(*) AS total FROM pecas WHERE status = 'disponivel'").fetchone()['total']
    total_vendidas = db.execute("SELECT COUNT(*) AS total FROM pecas WHERE status = 'vendida'").fetchone()['total']
    total_clientes = db.execute('SELECT COUNT(*) AS total FROM clientes').fetchone()['total']
    faturamento = db.execute('SELECT COALESCE(SUM(preco_vendido), 0) AS total FROM itens_venda').fetchone()['total']
    ticket_medio = db.execute(
        """
        SELECT COALESCE(ROUND(AVG(total_venda), 2), 0)
        FROM (
            SELECT SUM(iv.preco_vendido) AS total_venda
            FROM vendas v
            LEFT JOIN itens_venda iv ON iv.venda_id = v.id
            GROUP BY v.id
        )
        """
    ).fetchone()[0]

    categorias = db.execute(
        """
        SELECT c.nome, COUNT(p.id) AS total
        FROM categorias c
        LEFT JOIN pecas p ON p.categoria_id = c.id
        GROUP BY c.id, c.nome
        ORDER BY total DESC, c.nome ASC
        LIMIT 8
        """
    ).fetchall()

    pecas_paradas = db.execute(
        """
        SELECT p.*, c.nome AS categoria
        FROM pecas p
        JOIN categorias c ON c.id = p.categoria_id
        WHERE p.status = 'disponivel' AND date('now') - date(p.data_entrada) > 60
        ORDER BY p.data_entrada ASC
        """
    ).fetchall()

    categoria_max = max((item['total'] for item in categorias), default=0)
    return render_template(
        'dashboard.html',
        total_pecas=total_pecas,
        total_disponiveis=total_disponiveis,
        total_vendidas=total_vendidas,
        total_clientes=total_clientes,
        faturamento=faturamento,
        ticket_medio=ticket_medio,
        categorias=categorias,
        categoria_max=categoria_max,
        pecas_paradas=pecas_paradas,
    )


@app.route('/estoque')
@login_required
def estoque():
    db = get_db()
    status_atual = request.args.get('status', '')
    busca = request.args.get('q', '').strip()

    query = '''
        SELECT p.*, c.nome AS categoria
        FROM pecas p
        JOIN categorias c ON c.id = p.categoria_id
        WHERE 1 = 1
    '''
    params = []

    if status_atual:
        query += ' AND p.status = ?'
        params.append(status_atual)

    if busca:
        termo = f'%{busca}%'
        query += ' AND (p.descricao LIKE ? OR p.marca LIKE ? OR CAST(p.numero_peca AS TEXT) LIKE ? OR c.nome LIKE ?)'
        params.extend([termo, termo, termo, termo])

    query += ' ORDER BY p.data_entrada DESC'
    pecas = db.execute(query, params).fetchall()
    alertas = [peca for peca in pecas if peca['status'] == 'disponivel' and calcular_dias(peca['data_entrada']) > 60]

    return render_template('estoque.html', pecas=pecas, alertas=alertas, status_atual=status_atual, busca=busca)


@app.route('/pecas/nova', methods=['GET', 'POST'])
@login_required
def peca_nova():
    db = get_db()
    categorias = db.execute('SELECT * FROM categorias ORDER BY nome').fetchall()

    if request.method == 'POST':
        numero = request.form.get('numero_peca') or numero_peca_automatico(db)
        categoria_id = request.form.get('categoria_id')
        descricao = request.form.get('descricao', '').strip()
        marca = request.form.get('marca', '').strip()
        cor = request.form.get('cor', '').strip()
        tamanho = request.form.get('tamanho', '').strip()
        estado_conservacao = request.form.get('estado_conservacao', '').strip()
        preco_custo = valor_decimal(request.form.get('preco_custo'))
        preco_venda = valor_decimal(request.form.get('preco_venda'))
        status = request.form.get('status', 'disponivel')
        observacoes = request.form.get('observacoes', '').strip()
        foto = salvar_foto(request.files.get('foto'))
        data_entrada = request.form.get('data_entrada') or date.today().isoformat()

        try:
            db.execute(
                '''
                INSERT INTO pecas (
                    numero_peca, categoria_id, descricao, marca, cor, tamanho,
                    estado_conservacao, preco_custo, preco_venda, status, foto,
                    observacoes, data_entrada
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    int(numero), int(categoria_id), descricao, marca, cor, tamanho,
                    estado_conservacao, preco_custo, preco_venda, status, foto,
                    observacoes, data_entrada,
                ),
            )
            db.commit()
        except (ValueError, TypeError, sqlite3.IntegrityError):
            db.rollback()
            flash('Confira os dados da peça. O número deve ser único.', 'error')
            return render_template('peca_form.html', peca=None, categorias=categorias), 400
        return redirect(url_for('estoque'))

    return render_template('peca_form.html', peca=None, categorias=categorias)


@app.route('/pecas/editar/<int:peca_id>', methods=['GET', 'POST'])
@login_required
def peca_editar(peca_id):
    db = get_db()
    peca = db.execute('SELECT * FROM pecas WHERE id = ?', (peca_id,)).fetchone()
    if not peca:
        return redirect(url_for('estoque'))

    categorias = db.execute('SELECT * FROM categorias ORDER BY nome').fetchall()

    if request.method == 'POST':
        numero = request.form.get('numero_peca') or peca['numero_peca']
        categoria_id = request.form.get('categoria_id')
        descricao = request.form.get('descricao', '').strip()
        marca = request.form.get('marca', '').strip()
        cor = request.form.get('cor', '').strip()
        tamanho = request.form.get('tamanho', '').strip()
        estado_conservacao = request.form.get('estado_conservacao', '').strip()
        preco_custo = valor_decimal(request.form.get('preco_custo'))
        preco_venda = valor_decimal(request.form.get('preco_venda'))
        status = request.form.get('status', peca['status'])
        observacoes = request.form.get('observacoes', '').strip()
        foto_nova = salvar_foto(request.files.get('foto'))
        foto = foto_nova or peca['foto']

        try:
            db.execute(
                '''
                UPDATE pecas
                SET numero_peca = ?, categoria_id = ?, descricao = ?, marca = ?, cor = ?, tamanho = ?,
                    estado_conservacao = ?, preco_custo = ?, preco_venda = ?, status = ?, foto = ?,
                    observacoes = ?
                WHERE id = ?
                ''',
                (
                    int(numero), int(categoria_id), descricao, marca, cor, tamanho,
                    estado_conservacao, preco_custo, preco_venda, status, foto,
                    observacoes, peca_id,
                ),
            )
            db.commit()
        except (ValueError, TypeError, sqlite3.IntegrityError):
            db.rollback()
            flash('Confira os dados da peça. O número deve ser único.', 'error')
            return render_template('peca_form.html', peca=peca, categorias=categorias), 400
        return redirect(url_for('estoque'))

    return render_template('peca_form.html', peca=peca, categorias=categorias)


@app.route('/clientes')
@login_required
def clientes():
    db = get_db()
    clientes_lista = db.execute(
        '''
        SELECT c.*,
            (SELECT COUNT(*) FROM vendas v WHERE v.cliente_id = c.id) AS total_vendas,
            COALESCE((
                SELECT ROUND(AVG(total_venda), 2)
                FROM (
                    SELECT SUM(iv.preco_vendido) AS total_venda
                    FROM vendas v2
                    LEFT JOIN itens_venda iv ON iv.venda_id = v2.id
                    WHERE v2.cliente_id = c.id
                    GROUP BY v2.id
                )
            ), 0) AS ticket_medio
        FROM clientes c
        ORDER BY c.nome ASC
        '''
    ).fetchall()
    return render_template('clientes.html', clientes=clientes_lista)


@app.route('/clientes/novo', methods=['GET', 'POST'])
@login_required
def cliente_novo():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        whatsapp = request.form.get('whatsapp', '').strip()
        email = request.form.get('email', '').strip()
        data_cadastro = request.form.get('data_cadastro') or date.today().isoformat()

        db = get_db()
        db.execute(
            'INSERT INTO clientes (nome, whatsapp, email, data_cadastro) VALUES (?, ?, ?, ?)',
            (nome, whatsapp, email, data_cadastro),
        )
        db.commit()
        return redirect(url_for('clientes'))

    return render_template('cliente_form.html', cliente=None, today=date.today().isoformat())


@app.route('/vendas')
@login_required
def vendas():
    db = get_db()
    vendas_lista = db.execute(
        '''
        SELECT v.*, c.nome AS cliente,
            COUNT(iv.id) AS total_pecas,
            COALESCE(SUM(iv.preco_vendido), 0) + v.valor_frete AS valor_total
        FROM vendas v
        LEFT JOIN clientes c ON c.id = v.cliente_id
        LEFT JOIN itens_venda iv ON iv.venda_id = v.id
        GROUP BY v.id
        ORDER BY v.data_venda DESC
        '''
    ).fetchall()
    return render_template('vendas.html', vendas=vendas_lista)


@app.route('/vendas/nova', methods=['GET', 'POST'])
@login_required
def venda_nova():
    db = get_db()
    clientes = db.execute('SELECT * FROM clientes ORDER BY nome').fetchall()
    pecas_disponiveis = db.execute(
        "SELECT * FROM pecas WHERE status = 'disponivel' ORDER BY numero_peca ASC"
    ).fetchall()

    if request.method == 'POST':
        cliente_id = request.form.get('cliente_id')
        tipo_frete = request.form.get('tipo_frete', 'correios')
        valor_frete = float(request.form.get('valor_frete', 0) or 0)

        if tipo_frete == 'local_ssa':
            valor_frete = float(os.getenv('TAXA_LOCAL_SSA', '30'))

        pecas_selecionadas = request.form.getlist('peca_ids')
        if not cliente_id or not pecas_selecionadas:
            flash('Selecione um cliente e ao menos uma peça.', 'error')
            return redirect(url_for('venda_nova'))

        data_venda = request.form.get('data_venda') or date.today().isoformat()
        db.execute(
            'INSERT INTO vendas (cliente_id, data_venda, tipo_frete, valor_frete, status_venda, observacoes) VALUES (?, ?, ?, ?, ?, ?)',
            (int(cliente_id), data_venda, tipo_frete, valor_frete, 'pendente', request.form.get('observacoes', '')),
        )
        venda_id = db.execute('SELECT last_insert_rowid() AS id').fetchone()['id']

        for peca_id in pecas_selecionadas:
            peca = db.execute('SELECT * FROM pecas WHERE id = ?', (int(peca_id),)).fetchone()
            if not peca:
                continue
            preco = float(request.form.get(f'preco_{peca_id}', peca['preco_venda']) or peca['preco_venda'])
            db.execute(
                'INSERT INTO itens_venda (venda_id, peca_id, preco_vendido) VALUES (?, ?, ?)',
                (int(venda_id), int(peca_id), preco),
            )
            db.execute(
                "UPDATE pecas SET status = 'vendida', data_venda = ? WHERE id = ?",
                (data_venda, int(peca_id)),
            )

        db.commit()
        return redirect(url_for('vendas'))

    return render_template('venda_form.html', clientes=clientes, pecas_disponiveis=pecas_disponiveis, today=date.today().isoformat())


@app.route('/troca', methods=['GET', 'POST'])
@login_required
def troca():
    db = get_db()

    itens_vendidos = db.execute(
        '''
        SELECT iv.id, iv.venda_id, iv.peca_id, p.numero_peca, p.descricao, p.status,
               c.nome AS cliente, v.data_venda, iv.preco_vendido
        FROM itens_venda iv
        JOIN pecas p ON p.id = iv.peca_id
        JOIN vendas v ON v.id = iv.venda_id
        LEFT JOIN clientes c ON c.id = v.cliente_id
        WHERE p.status = 'vendida'
        ORDER BY v.data_venda DESC
        '''
    ).fetchall()

    if request.method == 'POST':
        item_venda_id = request.form.get('item_venda_id')
        data_devolucao = request.form.get('data_devolucao') or date.today().isoformat()
        peca_nova_id = request.form.get('peca_nova_id') or None
        diferenca_valor = float(request.form.get('diferenca_valor', 0) or 0)
        observacoes = request.form.get('observacoes', '').strip()

        item = db.execute(
            '''
            SELECT iv.*, v.data_venda, p.numero_peca, p.descricao
            FROM itens_venda iv
            JOIN vendas v ON v.id = iv.venda_id
            JOIN pecas p ON p.id = iv.peca_id
            WHERE iv.id = ?
            ''',
            (int(item_venda_id),),
        ).fetchone()

        if not item:
            flash('Item de venda não encontrado.', 'error')
            return redirect(url_for('troca'))

        dias = (datetime.strptime(data_devolucao, '%Y-%m-%d').date() - datetime.strptime(item['data_venda'], '%Y-%m-%d').date()).days
        if dias > 7:
            flash('Troca não permitida: o prazo máximo é de 7 dias corridos.', 'error')
            return redirect(url_for('troca'))

        db.execute(
            'INSERT INTO trocas (item_venda_id, data_devolucao, peca_nova_id, diferenca_valor, observacoes) VALUES (?, ?, ?, ?, ?)',
            (int(item_venda_id), data_devolucao, int(peca_nova_id) if peca_nova_id else None, diferenca_valor, observacoes),
        )

        if peca_nova_id:
            db.execute("UPDATE pecas SET status = 'vendida' WHERE id = ?", (int(peca_nova_id),))

        db.commit()
        flash('Troca registrada com sucesso.', 'success')
        return redirect(url_for('troca'))

    pecas_disponiveis = db.execute("SELECT * FROM pecas WHERE status = 'disponivel' ORDER BY numero_peca ASC").fetchall()
    return render_template('troca_form.html', itens_vendidos=itens_vendidos, pecas_disponiveis=pecas_disponiveis, today=date.today().isoformat())


@app.route('/trocas')
@login_required
def trocas_redirect():
    return redirect(url_for('troca'))


@app.route('/relatorios')
@login_required
def relatorios():
    db = get_db()
    total_vendas = db.execute('SELECT COUNT(*) AS total FROM vendas').fetchone()['total']
    faturamento = db.execute('SELECT COALESCE(SUM(preco_vendido), 0) AS total FROM itens_venda').fetchone()['total']
    peca_mais_vendida = db.execute(
        '''
        SELECT p.numero_peca, p.descricao, COUNT(iv.id) AS quantidade
        FROM itens_venda iv
        JOIN pecas p ON p.id = iv.peca_id
        GROUP BY p.id, p.numero_peca, p.descricao
        ORDER BY quantidade DESC, p.numero_peca ASC
        LIMIT 1
        '''
    ).fetchone()
    categorias = db.execute(
        '''
        SELECT c.nome, COUNT(p.id) AS total
        FROM categorias c
        LEFT JOIN pecas p ON p.categoria_id = c.id
        GROUP BY c.id, c.nome
        ORDER BY total DESC
        '''
    ).fetchall()

    return render_template(
        'relatorios.html',
        total_vendas=total_vendas,
        faturamento=faturamento,
        peca_mais_vendida=peca_mais_vendida,
        categorias=categorias,
    )


@app.route('/relatorios/pdf')
@login_required
def relatorio_pdf():
    if HTML is None:
        flash('A exportação PDF requer as bibliotecas nativas do WeasyPrint.', 'error')
        return redirect(url_for('relatorios'))

    db = get_db()
    total_vendas = db.execute('SELECT COUNT(*) AS total FROM vendas').fetchone()['total']
    faturamento = db.execute('SELECT COALESCE(SUM(preco_vendido), 0) AS total FROM itens_venda').fetchone()['total']
    peca_mais_vendida = db.execute(
        '''
        SELECT p.numero_peca, p.descricao, COUNT(iv.id) AS quantidade
        FROM itens_venda iv
        JOIN pecas p ON p.id = iv.peca_id
        GROUP BY p.id, p.numero_peca, p.descricao
        ORDER BY quantidade DESC, p.numero_peca ASC
        LIMIT 1
        '''
    ).fetchone()
    categorias = db.execute(
        '''
        SELECT c.nome, COUNT(p.id) AS total
        FROM categorias c
        LEFT JOIN pecas p ON p.categoria_id = c.id
        GROUP BY c.id, c.nome
        ORDER BY total DESC
        '''
    ).fetchall()

    html = render_template(
        'relatorio_pdf.html',
        total_vendas=total_vendas,
        faturamento=faturamento,
        peca_mais_vendida=peca_mais_vendida,
        categorias=categorias,
        data_geracao=date.today().isoformat(),
    )
    pdf_bytes = HTML(string=html).write_pdf()
    return send_file(BytesIO(pdf_bytes), mimetype='application/pdf', as_attachment=True, download_name='relatorio_fresh_sal_city.pdf')


@app.route('/health')
def health():
    return {'status': 'ok'}


if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
