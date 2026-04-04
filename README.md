# Calculadora de Salário Líquido e Tributos

Projeto de aplicação web desenvolvido como requisito para o curso de Análise e Desenvolvimento de Sistemas. A aplicação realiza o cálculo do salário líquido com base nas faixas progressivas reais do INSS e IRRF brasileiros, mantendo um histórico das simulações em banco de dados.

## Tecnologias Utilizadas
* **Back-end:** Python, Flask
* **Front-end:** HTML5, CSS3, Jinja2
* **Banco de Dados:** PostgreSQL
* **Controle de Versão:** Git, GitHub

## Etapas de Desenvolvimento (Roadmap)
O projeto foi estruturado para ser entregue em 4 fases incrementais (CRUD completo):

- [x] **Etapa 1:** Estrutura base (MVP), regras de negócio matemáticas (INSS/IRRF) e gravação no banco de dados (Create). Implementação de variáveis de ambiente para segurança (`.env`).
- [x] **Etapa 2:** Relacionamento de tabelas (Cargos), consultas SQL com `JOIN` e listagem do histórico na interface (Read).
- [ ] **Etapa 3:** Consultas de agregação (`SUM`/`COUNT`) para um Dashboard de totais e funcionalidade de exclusão de registros (Delete).
- [ ] **Etapa 4:** Filtros de busca personalizados e atualização de registros existentes (Update), fechando o ciclo do CRUD.
