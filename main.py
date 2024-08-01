from flask import Flask, render_template, request, redirect, url_for, make_response, jsonify
import pdfkit
import pymysql
import logging
from routes import register_blueprints

app = Flask(__name__)

# Configuração do pdfkit
path_wkhtmltopdf = 'C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe'
config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)


def get_db_connection():
    return pymysql.connect(user='root', password='melhor1@', host='127.0.0.1', database='demandas_geinfra_prod')

register_blueprints(app)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/cadastro_demanda_form', methods=['GET', 'POST'])
def cadastro_demanda_form():
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    if request.method == 'POST':
        unidade_id = request.form.get('unidade_id')
        tipo_servico_id = request.form.get('tipo_servico_id')
        descricao = request.form.get('descricao')
        status_id = request.form.get('status_id')
        data = request.form.get('data')

        app.logger.info(f'unidade_id: {unidade_id}')
        app.logger.info(f'tipo_servico_id: {tipo_servico_id}')
        app.logger.info(f'descricao: {descricao}')
        app.logger.info(f'status_id: {status_id}')
        app.logger.info(f'data: {data}')

        if not unidade_id or not tipo_servico_id or not descricao or not status_id or not data:
            cursor.close()
            conn.close()
            return "Erro: Todos os campos são obrigatórios.", 400

        cursor.execute('''
            INSERT INTO demandas (unidade_id, tipo_servico_id, descricao, status_id, data) 
            VALUES (%s, %s, %s, %s, %s)
        ''', (unidade_id, tipo_servico_id, descricao, status_id, data))
        
        conn.commit()

        cursor.execute('SELECT id, nome FROM unidades')
        unidades = cursor.fetchall()

        cursor.execute('SELECT id, descricao FROM tiposservico')
        tipos_servico = cursor.fetchall()

        cursor.execute('SELECT id, descricao FROM status')
        status = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('cadastro_demanda.html', success=True, unidades=unidades, tipos_servico=tipos_servico, status=status)

    cursor.execute('SELECT id, nome FROM unidades')
    unidades = cursor.fetchall()

    cursor.execute('SELECT id, descricao FROM tiposservico')
    tipos_servico = cursor.fetchall()

    cursor.execute('SELECT id, descricao FROM status')
    status = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('cadastro_demanda.html', unidades=unidades, tipos_servico=tipos_servico, status=status)

@app.route('/deletar_demanda/<int:id>', methods=['POST'])
def deletar_demanda(id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute('DELETE FROM ordem_servico_demandas WHERE demanda_id = %s', (id,))
    cursor.execute('DELETE FROM demandas WHERE id = %s', (id,))
    conn.commit()

    cursor.close()
    conn.close()

    return '', 204 


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
    SELECT d.id, u.nome as unidade_nome, u.id as unidade_id, ts.descricao as tipo_servico, d.descricao, s.id as status_id, s.descricao as status, d.data 
    FROM demandas d 
    JOIN unidades u ON d.unidade_id = u.id 
    JOIN tiposservico ts ON d.tipo_servico_id = ts.id 
    JOIN status s ON d.status_id = s.id
    '''
    filters = []
    params = []

    if request.method == 'POST':
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

    cursor.execute(query, params)
    demandas = cursor.fetchall()
    cursor.close()
    conn.close()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('demandas_table_body.html', demandas=demandas)

    return render_template('consultar_demandas.html', unidades=unidades, tipos_servico=tipos_servico, status=status, demandas=demandas)

@app.route('/atualizar_status_demanda/<int:id>', methods=['POST'])
def atualizar_status_demanda(id):
    status_id = request.form.get('status_id')
    
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute('UPDATE demandas SET status_id = %s WHERE id = %s', (status_id, id))
    conn.commit()

    cursor.close()
    conn.close()

    return '', 204  

@app.route('/criar_ordem_servico', methods=['GET', 'POST'])
def criar_ordem_servico():
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Fetch unidades, todas_demandas, and tecnicos before the request handling
    cursor.execute('SELECT id, nome FROM unidades')
    unidades = cursor.fetchall()

    cursor.execute('SELECT id, descricao FROM demandas')
    todas_demandas = cursor.fetchall()

    cursor.execute('SELECT id, nome FROM tecnico')
    tecnicos = cursor.fetchall()

    if request.method == 'POST':
        unidade_id = request.form.get('unidade_id')
        demanda_ids = request.form.getlist('demanda_ids')
        data_previsao = request.form.get('data_previsao')
        tecnicos_ids = request.form.getlist('tecnicos')
        observacoes = request.form.get('observacoes')

        app.logger.info(f'unidade_id: {unidade_id}')
        app.logger.info(f'demanda_ids: {demanda_ids}')
        app.logger.info(f'tecnicos_ids: {tecnicos_ids}')
        app.logger.info(f'data_previsao: {data_previsao}')
        app.logger.info(f'observacoes: {observacoes}')

        if not unidade_id or not demanda_ids:
            return "Erro: Unidade ou Demanda(s) não especificada(s).", 400

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
        return render_template('criar_ordem_servico.html', success=True, unidades=unidades, todas_demandas=todas_demandas, tecnicos=tecnicos)

    cursor.close()
    conn.close()

    return render_template('criar_ordem_servico.html', unidades=unidades, todas_demandas=todas_demandas, tecnicos=tecnicos)



@app.route('/get_demandas/<int:unidade_id>', methods=['GET'])
def get_demandas(unidade_id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    cursor.execute('SELECT id, descricao FROM demandas WHERE unidade_id = %s', (unidade_id,))
    demandas = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return jsonify(demandas)

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

@app.route('/gerar_pdf_executar/<int:ordem_servico_id>', methods=['GET'])
def gerar_pdf_executar(ordem_servico_id):
    try:
        # Get additional information from the request
        numero_sei = request.args.get('numero_sei')
        data_execucao_servico = request.args.get('data_execucao_servico')
        servicos_executados = request.args.get('servicos_executados')
        materiais_utilizados = request.args.get('materiais_utilizados')
        selected_demandas = request.args.get('demandas').split(',')

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

        # Filter demandas based on selected IDs
        cursor.execute('''
        SELECT d.id, d.descricao, ts.descricao as tipo_servico 
        FROM ordem_servico_demandas osd 
        JOIN demandas d ON osd.demanda_id = d.id 
        JOIN tiposservico ts ON d.tipo_servico_id = ts.id 
        WHERE osd.ordem_servico_id = %s AND d.id IN (%s)
        ''' % (ordem_servico_id, ','.join(['%s'] * len(selected_demandas))),
        tuple(selected_demandas))
        demandas = cursor.fetchall()

        cursor.execute('''
        SELECT t.nome
        FROM ordem_servico_tecnicos ost
        JOIN tecnico t ON ost.tecnico_id = t.id
        WHERE ost.ordem_servico_id = %s
        ''', (ordem_servico_id,))
        tecnicos = cursor.fetchall()

        # Update the status of the selected demandas to "Atendido"
        for demanda_id in selected_demandas:
            cursor.execute('''
            UPDATE demandas SET status_id = (SELECT id FROM status WHERE descricao = 'Atendido') 
            WHERE id = %s
            ''', (demanda_id,))
        
        conn.commit()
        cursor.close()
        conn.close()

        rendered = render_template('ordem_servico_pdf_executar.html',
                                   ordem_servico=ordem_servico,
                                   demandas=demandas,
                                   tecnicos=tecnicos,
                                   numero_sei=numero_sei,
                                   data_execucao_servico=data_execucao_servico,
                                   servicos_executados=servicos_executados,
                                   materiais_utilizados=materiais_utilizados)
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

@app.route('/executar_ordem_servico/<int:ordem_servico_id>')
def executar_ordem_servico(ordem_servico_id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    cursor.execute('''
    SELECT os.id as ordem_servico_id, u.nome as unidade_nome, os.data_criacao, os.data_previsao, os.observacoes
    FROM ordem_servico os 
    JOIN unidades u ON os.unidade_id = u.id
    WHERE os.id = %s
    ''', (ordem_servico_id,))
    ordem_servico = cursor.fetchone()

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
    
    if not ordem_servico:
        return 'Ordem de Serviço não encontrada', 404
    
    return render_template('executar_ordem_servico.html', ordem_servico=ordem_servico, demandas=demandas, tecnicos=tecnicos)


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

    cursor.execute(query, params)
    ordens_servico = cursor.fetchall()
    cursor.close()
    conn.close()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('ordens_table_body.html', ordens_servico=ordens_servico)

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute('SELECT id, nome FROM unidades')
    unidades = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('consultar_ordens_servico.html', ordens_servico=ordens_servico, unidades=unidades)

@app.route('/deletar_ordem_servico/<int:id>', methods=['POST'])
def deletar_ordem_servico(id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    try:
        # Delete dependent records in ordem_servico_tecnicos first
        cursor.execute('DELETE FROM ordem_servico_tecnicos WHERE ordem_servico_id = %s', (id,))
        
        # Delete dependent records in ordem_servico_demandas
        cursor.execute('DELETE FROM ordem_servico_demandas WHERE ordem_servico_id = %s', (id,))
        
        # Now delete the ordem_servico
        cursor.execute('DELETE FROM ordem_servico WHERE id = %s', (id,))
        
        conn.commit()
    except pymysql.err.IntegrityError as ie:
        conn.rollback()
        print(f"Integrity error: {str(ie)}")
        return jsonify({'error': 'Integrity error: ' + str(ie)}), 500
    except Exception as e:
        conn.rollback()
        print(f"General error: {str(e)}")
        return jsonify({'error': 'General error: ' + str(e)}), 500
    finally:
        cursor.close()
        conn.close()

    return '', 204



@app.route('/ordem_servico/<int:id>', methods=['GET'])
def visualizar_ordem_servico(id):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    query = '''
    SELECT os.id as ordem_servico_id, u.nome as unidade_nome, os.data_criacao, os.data_previsao, os.observacoes
    FROM ordem_servico os 
    JOIN unidades u ON os.unidade_id = u.id
    WHERE os.id = %s
    '''
    
    cursor.execute(query, (id,))
    ordem_servico = cursor.fetchone()
    cursor.close()
    conn.close()

    if ordem_servico is None:
        return jsonify({'error': 'Ordem de Serviço não encontrada'}), 404

    # Formatando as datas para o formato YYYY-MM-DD
    ordem_servico['data_criacao'] = ordem_servico['data_criacao'].strftime('%Y-%m-%d') if ordem_servico['data_criacao'] else ''
    ordem_servico['data_previsao'] = ordem_servico['data_previsao'].strftime('%Y-%m-%d') if ordem_servico['data_previsao'] else ''

    return jsonify(ordem_servico)

@app.route('/atualizar_ordem_servico', methods=['POST'])
def atualizar_ordem_servico():
    ordem_servico_id = request.form.get('ordem_servico_id')
    data_criacao = request.form.get('data_criacao')
    data_previsao = request.form.get('data_previsao')
    observacoes = request.form.get('observacoes')

    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = '''
    UPDATE ordem_servico
    SET data_criacao = %s, data_previsao = %s, observacoes = %s
    WHERE id = %s
    '''
    
    cursor.execute(query, (data_criacao, data_previsao, observacoes, ordem_servico_id))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'success': 'Ordem de Serviço atualizada com sucesso'})


if __name__ == '__main__':
    app.run(debug=True, port=8080)

