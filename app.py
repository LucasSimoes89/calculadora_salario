from flask import Flask, render_template, request
import psycopg2

app = Flask(__name__)

# Configuração da conexão com o banco de dados
DB_CONFIG = {
    'dbname': 'calculadora_tributos',
    'user': 'postgres', # Substitua pelo seu usuário
    'password': '123',  # Substitua pela sua senha
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
    
    if request.method == 'POST':
        # Recebe os dados do Front-end
        salario_bruto = float(request.form['salario_bruto'])
        dependentes = int(request.form['dependentes'])
        
        # Executa a regra de negócio
        inss, irrf, salario_liquido = calcular_tributos(salario_bruto, dependentes)
        
        # Salva no Banco de Dados (Create do CRUD)
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO calculos (salario_bruto, dependentes, inss, irrf, salario_liquido)
            VALUES (%s, %s, %s, %s, %s)
        ''', (salario_bruto, dependentes, inss, irrf, salario_liquido))
        conn.commit()
        cur.close()
        conn.close()
        
        # Prepara o dicionário para exibir no HTML
        resultado = {
            'bruto': salario_bruto,
            'dependentes': dependentes,
            'inss': inss,
            'irrf': irrf,
            'liquido': salario_liquido
        }
        
    return render_template('index.html', resultado=resultado)

if __name__ == '__main__':
    app.run(debug=True)