from flask import Flask, jsonify, render_template, request, make_response, redirect, session, url_for, flash
from flask_cors import CORS
from dotenv import load_dotenv
from os import getenv
from mysql.connector import connect
import utils

app = Flask(__name__)
CORS(app)
load_dotenv()
app.secret_key = f'{getenv("FLASK_SECRET_KEY")}'
# Rotas das Páginas 

@app.route("/", methods=["GET"])
def index():
  return render_template("index.html")

@app.route("/criar-conta", methods=["GET"])
def criar_conta():
  return render_template("crie_conta.html")

@app.route("/login", methods=["GET", "POST"])
def logar():
    cnx = connect(
      host=getenv("DB_HOST"),
      port=getenv("DB_PORT"),
      user=getenv("DB_USER"),
      password=getenv("DB_PASSW"),
      database=getenv("DB_NAME"))
    cursor = cnx.cursor(buffered=True)
    if 'loggedin' in session:
        return redirect(url_for('dashboard'))
    else:
        if request.method == 'POST' and 'email' in request.form and 'senha' in request.form:
            email = request.form['email']
            senha = request.form['senha']
            cursor.execute('SELECT * FROM Usuarios WHERE email = %s', (email,))
            contas = cursor.fetchone()
            if contas:
                usuarioId = contas[0]
                print(usuarioId)
                cursor.execute("SELECT senha FROM Senhas WHERE passwordOwnerId = %s", (usuarioId,))
                senhas = cursor.fetchone()
                for i in senhas:
                   senha_hashed = i
                if utils.check_password_hash_md5(password=senha, hash=senha_hashed):
                    session['loggedin'] = True
                    session['id'] = usuarioId
                    session['email'] = contas[2]
                    session['nome'] = contas[1]
                    session['tipoInstituicao'] = contas[3]
                    session['cargo'] = contas[4]
                    return redirect(url_for('dashboard'))
                else:
                    return make_response(jsonify({"error": True, "message": "E-mail ou senha inválidos"}), 401)
            else:
                return make_response(jsonify({"error": True, "message": "E-mail ou senha inválidos"}), 401)
            
    return render_template("login.html")

@app.route("/dashboard", methods=["GET"])
def dashboard():
  if 'loggedin' in session: 
    return render_template("dashboard.html")
  else:
     return redirect(url_for('login'))

@app.route("/minha-conta", methods=["GET"])
def minha_conta():
  if 'loggedin' in session:
    return render_template("minha_conta.html", nomeCompleto=session['nome'], email=session['email'], nomeInstituicao=session['tipoInstituicao'])

  return redirect(url_for('login'))

@app.route("/recuperar-senha", methods=["GET"])
def recuperar_senha():
  return render_template("recu_senha.html")

@app.route("/logout")
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('email', None)
    session.pop('nome', None)
    session.pop('instituicao', None)
    return redirect(url_for('login'))

# REST API

@app.route("/api/v1/register", methods=["GET", "POST"])
def register_user():
  try:
    cnx = connect(
      host=getenv("DB_HOST"),
      port=getenv("DB_PORT"),
      user=getenv("DB_USER"),
      password=getenv("DB_PASSW"),
      database=getenv("DB_NAME"))
    cursor = cnx.cursor(buffered=True)
    nome = request.json["nome"]
    email = request.json["email"]
    senha = request.json["senha"]
    cargo = "ALUNO" # request.json["cargo"]
    instituicao = request.json["instituicao"]
    print(nome, email, senha, instituicao)
    query_register = f'INSERT INTO Usuarios (nomeCompleto, email, instituicaoTipo, cargo) VALUES ("{nome}", "{email}", "{instituicao}", "{cargo}")'
    query_getUsuarioId = f'SELECT idUsuario FROM Usuarios WHERE email = "{email}"'
    cursor.execute(query_register)
    cnx.commit()
    cursor.execute(query_getUsuarioId)
    for userId in cursor.fetchone():
      usuarioId = userId
    query_senha = f'INSERT INTO Senhas (passwordOwnerId, senha) VALUES ("{usuarioId}", MD5("{senha}"))'
    cursor.execute(query_senha)
    cnx.commit()
    cursor.close()
    cnx.close()
    return make_response(jsonify({"success": True, "message": "Usuário criado com sucesso!"}), 200)
  except Exception as e:
    return make_response(jsonify({"error": True, "message": str(e)}), 500)


@app.route("/api/v1/get-tarefas")
def get_tarefas():
   try:
      tarefas = [{}]
      cnx = connect(
        host=getenv("DB_HOST"),
        port=getenv("DB_PORT"),
        user=getenv("DB_USER"),
        password=getenv("DB_PASSW"),
        database=getenv("DB_NAME"))
      cursor = cnx.cursor(buffered=True)
      idUsuario = request.json['idUsuario']
      if session['idUsuario'] == idUsuario:
         cursor.execute("")
         make_response(jsonify({"success": True, "tarefas": tarefas}), 200)
      return tarefas
   except Exception as e:
      return make_response(jsonify({"error": True, "message": str(e)}), 500)

@app.route("/api/v1/add-new-tarefa", methods=["POST"])
def new_tarefa():
  try:
    cnx = connect(
      host=getenv("DB_HOST"),
      port=getenv("DB_PORT"),
      user=getenv("DB_USER"),
      password=getenv("DB_PASSW"),
      database=getenv("DB_NAME"))
    cursor = cnx.cursor(buffered=True)
    idUsuario = request.json['idUsuario']
    if session['idUsuario'] == idUsuario:     
      titulo = request.json['titulo']
      descricao = 'Sem descrição' # request.json['descricao']
      cursor.execute(f'INSERT INTO Tarefas (idDonoDaTarefa, tituloTarefa, descricaoTarefa, dataDeCriacao, tarefaConcluida) VALUES ({idUsuario}, {titulo}, {descricao}, NOW(), True)')
      cnx.commit()
      return make_response(jsonify({"success": True, "message": "Nova tarefa adicionada com sucesso!"}), 200)
    else:
       return make_response(jsonify({"error": True,"message": "Você não pode criar uma tarefa para outro usuário."}), 401)
  except Exception as e:
     return make_response(jsonify({"error": True, "message": str(e)}), 500)

@app.route("/api/v1/concluir-tarefa", methods=["POST"])
def concluir_tarefa():
   try:
      cnx = connect(
        host=getenv("DB_HOST"),
        port=getenv("DB_PORT"),
        user=getenv("DB_USER"),
        password=getenv("DB_PASSW"),
        database=getenv("DB_NAME"))
      cursor = cnx.cursor(buffered=True)
      idUsuario = request.json["idUsuario"]
      if session['idUsuario'] == idUsuario:
        cursor.execute(f'UPDATE Tarefas SET tarefaConcluida = true WHERE idDonoDaTarefa = {idUsuario};')
        return make_response(jsonify({"success": True, "message": "Tarefa conclúida com sucesso!"}), 200)
      else:
         return make_response(jsonify({"error": True, "message": "Você não pode concluir tarefas de outro usuário!"}), 401)
   except Exception as e:
      return make_response(jsonify({"error": True, "message": str(e)}), 500)

if __name__ in "__main__":
  app.run(host="127.0.0.1", port=5000, debug=True)