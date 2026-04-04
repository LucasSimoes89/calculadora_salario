import os
from flask import Flask, render_template, request
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
    
    # 2. Busca o histórico de cálculos unindo as tabelas (JOIN)
    cur.execute('''
        SELECT c.id, cg.nome_cargo, c.salario_bruto, c.salario_liquido, c.data_calculo 
        FROM calculos c
        JOIN cargos cg ON c.cargo_id = cg.id
        ORDER BY c.data_calculo DESC
        LIMIT 10
    ''')
    historico_calculos = cur.fetchall()

    cur.close()
    conn.close()
        
    return render_template('index.html', resultado=resultado, cargos=lista_cargos, historico=historico_calculos)

if __name__ == '__main__':
    app.run(debug=True)