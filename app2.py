from flask import Flask, render_template, request, redirect, url_for, make_response
import pdfkit
import pymysql
import logging

app = Flask(__name__)

# Configuração do pdfkit
path_wkhtmltopdf = 'C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe'
config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)


def get_db_connection():
    return pymysql.connect(user='root', password='melhor1@', host='127.0.0.1', database='demandas_geinfra_dev')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/consultar_demandas', methods=['GET', 'POST'])
def consultar_demandas():
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute('SELECT id, nome FROM unidades')
    unidades = cursor.fetchall()

    cursor.execute('SELECT id, descricao FROM tiposservico')
    tipos_servico = cursor.fetchall()

    cursor.execute('SELECT id, descricao FROM status')
    status = cursor.fetchall()

    query = '''
    SELECT d.id, u.nome as unidade_nome, u.id as unidade_id, ts.descricao as tipo_servico, d.descricao, s.descricao as status, d.data 
    FROM demandas d 
    JOIN unidades u ON d.unidade_id = u.id 
    JOIN tiposservico ts ON d.tipo_servico_id = ts.id 
    JOIN status s ON d.status_id = s.id
    '''
    filters = []
    params = []

    if request.method == 'POST':
        if 'filtrar' in request.form:
            id_filter = request.form.get('id_filter')
            unidade_filter = request.form.get('unidade_filter')
            tipo_servico_filter = request.form.get('tipo_servico_filter')
            status_filter = request.form.get('status_filter')
            data_filter = request.form.get('data_filter')

            if id_filter:
                filters.append('d.id = %s')
                params.append(id_filter)
            if unidade_filter:
                filters.append('d.unidade_id = %s')
                params.append(unidade_filter)
            if tipo_servico_filter:
                filters.append('d.tipo_servico_id = %s')
                params.append(tipo_servico_filter)
            if status_filter:
                filters.append('d.status_id = %s')
                params.append(status_filter)
            if data_filter:
                filters.append('DATE(d.data) = %s')
                params.append(data_filter)

            if filters:
                query += ' WHERE ' + ' AND '.join(filters)

        if 'criar_ordem_servico' in request.form:
            demanda_ids = request.form.getlist('demanda_ids')
            unidade_id = request.form.get('unidade_id')
            if demanda_ids and unidade_id:
                return redirect(url_for('criar_ordem_servico', demanda_ids=','.join(demanda_ids), unidade_id=unidade_id))
            else:
                mensagem = "Nenhuma demanda selecionada"
                return render_template('consultar_demandas.html', unidades=unidades, tipos_servico=tipos_servico, status=status, demandas=demandas, mensagem=mensagem)

    cursor.execute(query, params)
    demandas = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('consultar_demandas.html', unidades=unidades, tipos_servico=tipos_servico, status=status, demandas=demandas)





@app.route('/criar_ordem_servico', methods=['GET', 'POST'])
def criar_ordem_servico():
    demanda_ids = request.args.get('demanda_ids')
    unidade_id = request.args.get('unidade_id')

    if not demanda_ids:
        return "Erro: Nenhuma demanda selecionada.", 400

    demanda_ids = demanda_ids.split(',')

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    if request.method == 'POST':
        data_previsao = request.form.get('data_previsao')
        tecnicos_ids = request.form.getlist('tecnicos')
        observacoes = request.form.get('observacoes')

        # Logs para depuração
        app.logger.info(f'unidade_id: {unidade_id}')
        app.logger.info(f'demanda_ids: {demanda_ids}')
        app.logger.info(f'tecnicos_ids: {tecnicos_ids}')
        app.logger.info(f'data_previsao: {data_previsao}')
        app.logger.info(f'observacoes: {observacoes}')

        # Verificação se unidade_id está None
        if not unidade_id:
            return "Erro: Unidade não especificada.", 400

        # Insere a nova ordem de serviço no banco de dados
        cursor.execute('INSERT INTO ordem_servico (unidade_id, data_previsao, observacoes) VALUES (%s, %s, %s)',
                       (unidade_id, data_previsao, observacoes))
        ordem_servico_id = cursor.lastrowid

        for demanda_id in demanda_ids:
            cursor.execute('INSERT INTO ordem_servico_demandas (ordem_servico_id, demanda_id) VALUES (%s, %s)',
                           (ordem_servico_id, demanda_id))

        for tecnico_id in tecnicos_ids:
            cursor.execute('INSERT INTO ordem_servico_tecnicos (ordem_servico_id, tecnico_id) VALUES (%s, %s)',
                           (ordem_servico_id, tecnico_id))

        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for('ver_ordem_servico', ordem_servico_id=ordem_servico_id))

    cursor.execute('SELECT id, nome FROM unidades WHERE id = %s', (unidade_id,))
    unidade = cursor.fetchone()

    cursor.execute('''
    SELECT d.id, d.descricao, ts.descricao as tipo_servico 
    FROM demandas d 
    JOIN tiposservico ts ON d.tipo_servico_id = ts.id 
    WHERE d.id IN (%s)
    ''' % ','.join('%s' for _ in demanda_ids), demanda_ids)
    demandas = cursor.fetchall()

    cursor.execute('SELECT id, nome FROM tecnico')
    tecnicos = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('criar_ordem_servico.html', unidade=unidade, demandas=demandas, tecnicos=tecnicos)






@app.route('/ver_ordem_servico/<int:ordem_servico_id>', methods=['GET'])
def ver_ordem_servico(ordem_servico_id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute('SELECT * FROM ordem_servico WHERE id = %s', (ordem_servico_id,))
    ordem_servico = cursor.fetchone()

    cursor.execute('SELECT * FROM unidades WHERE id = %s', (ordem_servico['unidade_id'],))
    unidade = cursor.fetchone()

    cursor.execute('''
    SELECT d.id, d.descricao, ts.descricao as tipo_servico 
    FROM ordem_servico_demandas osd
    JOIN demandas d ON osd.demanda_id = d.id
    JOIN tiposservico ts ON d.tipo_servico_id = ts.id
    WHERE osd.ordem_servico_id = %s
    ''', (ordem_servico_id,))
    demandas = cursor.fetchall()

    cursor.execute('''
    SELECT t.id, t.nome
    FROM ordem_servico_tecnicos ost
    JOIN tecnico t ON ost.tecnico_id = t.id
    WHERE ost.ordem_servico_id = %s
    ''', (ordem_servico_id,))
    tecnicos = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('ver_ordem_servico.html', ordem_servico=ordem_servico, unidade=unidade, demandas=demandas, tecnicos=tecnicos)



@app.route('/gerar_pdf/<int:ordem_servico_id>')
def gerar_pdf(ordem_servico_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        cursor.execute('''
        SELECT os.id as ordem_servico_id, u.nome as unidade_nome, os.data_criacao, os.data_previsao, os.observacoes
        FROM ordem_servico os 
        JOIN unidades u ON os.unidade_id = u.id 
        WHERE os.id = %s
        ''', (ordem_servico_id,))
        ordem_servico = cursor.fetchone()

        if not ordem_servico:
            logging.error(f"Ordem de serviço com ID {ordem_servico_id} não encontrada.")
            return "Ordem de serviço não encontrada", 404

        cursor.execute('''
        SELECT d.id, d.descricao, ts.descricao as tipo_servico 
        FROM ordem_servico_demandas osd 
        JOIN demandas d ON osd.demanda_id = d.id 
        JOIN tiposservico ts ON d.tipo_servico_id = ts.id 
        WHERE osd.ordem_servico_id = %s
        ''', (ordem_servico_id,))
        demandas = cursor.fetchall()

        cursor.execute('''
        SELECT t.nome
        FROM ordem_servico_tecnicos ost
        JOIN tecnico t ON ost.tecnico_id = t.id
        WHERE ost.ordem_servico_id = %s
        ''', (ordem_servico_id,))
        tecnicos = cursor.fetchall()

        cursor.close()
        conn.close()

        rendered = render_template('ordem_servico_pdf.html', ordem_servico=ordem_servico, demandas=demandas, tecnicos=tecnicos)
        pdf = pdfkit.from_string(rendered, False, configuration=config)

        if not pdf:
            logging.error(f"Falha na geração do PDF para a ordem de serviço com ID {ordem_servico_id}.")
            return "Erro ao gerar o PDF", 500

        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=ordem_servico_{ordem_servico_id}.pdf'

        return response
    except Exception as e:
        logging.error(f"Erro na geração do PDF para a ordem de serviço com ID {ordem_servico_id}: {str(e)}")
        return f"Erro ao gerar o PDF: {str(e)}", 500


@app.route('/cadastro_tecnico')
def cadastro_tecnico():
    return render_template('cadastro_tecnico.html')

@app.route('/consultar_ordens_servico', methods=['GET', 'POST'])
def consultar_ordens_servico():
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    query = '''
    SELECT os.id as ordem_servico_id, u.nome as unidade_nome, os.data_criacao, os.data_previsao, os.observacoes
    FROM ordem_servico os 
    JOIN unidades u ON os.unidade_id = u.id
    '''
    filters = []
    params = []

    if request.method == 'POST':
        ordem_servico_id_filter = request.form.get('ordem_servico_id_filter')
        unidade_filter = request.form.get('unidade_filter')
        data_criacao_filter = request.form.get('data_criacao_filter')
        data_previsao_filter = request.form.get('data_previsao_filter')

        app.logger.info(f'Filtro ID: {ordem_servico_id_filter}')
        app.logger.info(f'Filtro Unidade: {unidade_filter}')
        app.logger.info(f'Filtro Data de Criação: {data_criacao_filter}')
        app.logger.info(f'Filtro Data de Previsão: {data_previsao_filter}')

        if ordem_servico_id_filter:
            filters.append('os.id = %s')
            params.append(ordem_servico_id_filter)
        if unidade_filter:
            filters.append('os.unidade_id = %s')
            params.append(unidade_filter)
        if data_criacao_filter:
            filters.append('DATE(os.data_criacao) = %s')
            params.append(data_criacao_filter)
        if data_previsao_filter:
            filters.append('DATE(os.data_previsao) = %s')
            params.append(data_previsao_filter)

        if filters:
            query += ' WHERE ' + ' AND '.join(filters)

    app.logger.info(f'Query: {query}')
    app.logger.info(f'Params: {params}')

    cursor.execute(query, params)
    ordens_servico = cursor.fetchall()
    cursor.close()
    conn.close()

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute('SELECT id, nome FROM unidades')
    unidades = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('consultar_ordens_servico.html', ordens_servico=ordens_servico, unidades=unidades)




if __name__ == '__main__':
    app.run(debug=True, port=8080)

