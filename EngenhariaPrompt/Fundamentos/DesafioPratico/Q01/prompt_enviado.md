
# Enunciado
A Hill Valley Tech é uma empresa fictícia que serve de palco para este desafio.
Tem cinco sistemas em produção, cada um com seu papel bem definido.

-  O Chronos é o API gateway e a plataforma core, ponto de entrada de todo tráfego da empresa.
-  Por trás dele, o Ledger é um data warehouse em PostgreSQL que guarda histórico de transações e eventos,
-  enquanto o Reactor toca o processamento assíncrono por filas de mensagens.
-  Em paralelo a tudo isso, o Beacon mantém a observabilidade do ambiente inteiro, métricas, logs e alertas, e
é por ele que o plantão enxerga o que está acontecendo.
-  Fora do core principal, o Lift é um produto em beta que o time vem amadurecendo à parte.

Quero utilizar o framework RTF (Role, tash e Format)

# Role (skill do executor do prompt): Atuar como engenheiro senior de devops com conhecimento de docker e kubernetes e usar as boas práticas de segurança.

# Task (O que preisa ser feito): Criar um Dockerfile em produção seguindo as especificações:

- O Lift vai sair das VMs onde vem rodando e entrar no cluster Kubernetes da empresa. 
O código já está pronto: uma API Python/Flask na porta 8080, dependências declaradas em requirements.txt, 
e duas variáveis de ambiente que precisam estar presentes no runtime, DATABASE_URL e API_KEY.

- O serviço sobe com gunicorn --bind 0.0.0.0:8080 --workers 4 app:app

- Seguir todas as boas práticas de criação.

- Conteúdo de requirements.txt:
Flask==3.0.0
gunicorn==21.2.0
requests==2.31.0
python-dotenv==1.0.0
psycopg2-binary==2.9.9

- A esgtrutura do projeto:

lift/
├── app.py
├── requirements.txt
├── lib/
│   ├── auth.py
│   └── storage.py
└── tests/
    └── test_app.py

# Format (saídas do prompt):
- Dockerfile e um arquivo de justicativa de cada passo deste arquivo gerado.

