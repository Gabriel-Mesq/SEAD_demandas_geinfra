from flask import Blueprint, render_template, request, redirect, url_for
from config import get_db_connection, app  # Importa de config.py
import pymysql

tecnico_bp = Blueprint('tecnico', __name__)

@tecnico_bp.route('/cadastro_tecnico')
def cadastro_tecnico():
    return render_template('cadastro_tecnico.html')

@tecnico_bp.route('/cadastro_tecnico_form', methods=['GET', 'POST'])
def cadastro_tecnico_form():
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    if request.method == 'POST':
        nome = request.form.get('nome')
        especialidade = request.form.get('especialidade')
        contato = request.form.get('contato')

        # Logs for debugging
        app.logger.info(f'nome: {nome}')
        app.logger.info(f'especialidade: {especialidade}')
        app.logger.info(f'contato: {contato}')

        # Check if any required field is missing
        if not nome or not especialidade or not contato:
            return "Erro: Todos os campos são obrigatórios.", 400

        # Insert the new technician into the database
        cursor.execute('INSERT INTO tecnico (nome) VALUES (%s)',
                       (nome,))
        
        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for('tecnico.cadastro_tecnico_success'))  # Use o nome completo do endpoint

    cursor.close()
    conn.close()

    return render_template('cadastro_tecnico.html')

@tecnico_bp.route('/cadastro_tecnico_success')
def cadastro_tecnico_success():
    return render_template('cadastro_tecnico.html', success=True)
