import os
import csv
import io
from flask import Flask, render_template, request, redirect, url_for, Response
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

app = Flask(__name__)

# Configuração da conexão com o banco de dados puxando do .env
DB_CONFIG = {
    'dbname': 'calculadora_tributos',
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': 'localhost',
    'port': '5432'
}

def get_db_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    return conn

def calcular_tributos(salario_bruto, dependentes):
    # Regra de negócio: Cálculo simplificado do INSS (Progressivo)
    if salario_bruto <= 1412.00:
        inss = salario_bruto * 0.075
    elif salario_bruto <= 2666.68:
        inss = salario_bruto * 0.09 - 21.18
    elif salario_bruto <= 4000.03:
        inss = salario_bruto * 0.12 - 101.18
    else:
        inss = salario_bruto * 0.14 - 181.18
    
    # Teto simplificado do INSS
    if inss > 908.85:
        inss = 908.85

    # Regra de negócio: Cálculo do IRRF (Base de cálculo = Bruto - INSS - Dependentes)
    deducao_dependente = dependentes * 189.59
    base_calculo = salario_bruto - inss - deducao_dependente

    if base_calculo <= 2259.20:
        irrf = 0.0
    elif base_calculo <= 2826.65:
        irrf = base_calculo * 0.075 - 169.44
    elif base_calculo <= 3751.05:
        irrf = base_calculo * 0.15 - 381.44
    elif base_calculo <= 4664.68:
        irrf = base_calculo * 0.225 - 662.77
    else:
        irrf = base_calculo * 0.275 - 896.00
    
    if irrf < 0:
        irrf = 0.0

    salario_liquido = salario_bruto - inss - irrf
    
    return round(inss, 2), round(irrf, 2), round(salario_liquido, 2)

@app.route('/', methods=['GET', 'POST'])
def index():
    resultado = None
    conn = get_db_connection()
    
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if request.method == 'POST':
        # Recebe os dados do Front-end
        cargo_id = int(request.form['cargo']) # Recebe o cargo selecionado
        salario_bruto = float(request.form['salario_bruto'])
        dependentes = int(request.form['dependentes'])
        
        # Executa a regra de negócio
        inss, irrf, salario_liquido = calcular_tributos(salario_bruto, dependentes)
        
        # Salva no Banco de Dados (Create do CRUD)
        cur.execute('''
            INSERT INTO calculos (cargo_id, salario_bruto, dependentes, inss, irrf, salario_liquido)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (cargo_id, salario_bruto, dependentes, inss, irrf, salario_liquido))
        conn.commit()
        
        # Prepara o dicionário para exibir no HTML
        resultado = {
            'bruto': salario_bruto,
            'dependentes': dependentes,
            'inss': inss,
            'irrf': irrf,
            'liquido': salario_liquido
        }
        
    # --- LEITURA DE DADOS (READ) ---
    
    # 1. Busca os cargos para montar as opções no Front-end
    cur.execute("SELECT id, nome_cargo FROM cargos ORDER BY nome_cargo")
    lista_cargos = cur.fetchall()
    
    # LÓGICA DE PAGINAÇÃO
    pagina_atual = request.args.get('pagina', 1, type=int) 
    itens_por_pagina = 5
    offset = (pagina_atual - 1) * itens_por_pagina 

    # Conta o total de registros para saber quantas páginas existem
    cur.execute('''
        SELECT COUNT(c.id) as total 
        FROM calculos c
        JOIN cargos cg ON c.cargo_id = cg.id
    ''')
    total_registros = cur.fetchone()['total']
    total_paginas = (total_registros + itens_por_pagina - 1) // itens_por_pagina if total_registros > 0 else 1

    # 2. Busca o histórico com LIMIT e OFFSET (Paginação)
    cur.execute('''
        SELECT c.id, cg.nome_cargo, c.salario_bruto, c.salario_liquido, c.data_calculo 
        FROM calculos c
        JOIN cargos cg ON c.cargo_id = cg.id
        ORDER BY c.data_calculo DESC
        LIMIT %s OFFSET %s
    ''', (itens_por_pagina, offset))
    historico_calculos = cur.fetchall()

    cur.close()
    conn.close()
        
    return render_template('index.html', resultado=resultado, cargos=lista_cargos, 
                           historico=historico_calculos, totais=total_registros,
                           pagina_atual=pagina_atual, total_paginas=total_paginas)

# Rota para deletar um registro específico
@app.route('/deletar/<int:id>', methods=['POST'])
def deletar(id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Executa o DELETE no banco de dados usando o ID recebido na URL
    cur.execute('DELETE FROM calculos WHERE id = %s', (id,))
    conn.commit()
    
    cur.close()
    conn.close()
    
    # Redireciona o usuário de volta para a rota principal ('index')
    return redirect(url_for('index'))

# Rota para Exportar linha específica para CSV 
@app.route('/exportar/<int:id>', methods=['GET'])
def exportar_csv(id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Busca o detalhamento completo apenas do ID solicitado
    cur.execute('''
        SELECT c.id, cg.nome_cargo, c.salario_bruto, c.dependentes, c.inss, c.irrf, c.salario_liquido, c.data_calculo 
        FROM calculos c
        JOIN cargos cg ON c.cargo_id = cg.id
        WHERE c.id = %s
    ''', (id,))
    calculo = cur.fetchone()
    cur.close()
    conn.close()

    if not calculo:
        return redirect(url_for('index'))

    # Gera o CSV na memória (sem salvar arquivo físico no servidor)
    saida_memoria = io.StringIO()
    saida_memoria.write('\ufeff')
    writer = csv.writer(saida_memoria, delimiter=';')
    
    # Escreve o cabeçalho das colunas
    writer.writerow(['ID', 'Data', 'Cargo', 'Salário Bruto', 'Dependentes', 'INSS', 'IRRF', 'Salário Líquido'])
    
    # Escreve os dados da linha
    writer.writerow([
        calculo['id'], 
        calculo['data_calculo'].strftime('%d/%m/%Y %H:%M'), 
        calculo['nome_cargo'], 
        f"R$ {calculo['salario_bruto']:.2f}",
        calculo['dependentes'],
        f"R$ {calculo['inss']:.2f}",
        f"R$ {calculo['irrf']:.2f}",
        f"R$ {calculo['salario_liquido']:.2f}"
    ])

    return Response(
        saida_memoria.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment;filename=calculo_{id}.csv"}
    )

if __name__ == '__main__':
    app.run(debug=True)