from flask import Flask, jsonify, render_template, request, make_response, redirect, session, url_for, flash
from flask_cors import CORS
from dotenv import load_dotenv
from os import getenv
from mysql.connector import connect
import utils
import smtplib
import email.message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import uuid

app = Flask(__name__)
CORS(app)
load_dotenv()
app.secret_key = f'{getenv("FLASK_SECRET_KEY")}'
s = smtplib.SMTP('smtp-mail.outlook.com', port=587)
s.starttls()
s.login(getenv("EMAIL_RECUPERACAO_DE_SENHA"), getenv("SENHA"))
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
    print(session['id'])
    print(session)
    return render_template("dashboard.html")
  else:
     return redirect(url_for('logar'))

@app.route("/minha-conta", methods=["GET"])
def minha_conta():
  if 'loggedin' in session:
    return render_template("minha_conta.html", nomeCompleto=session['nome'], email=session['email'], nomeInstituicao=session['tipoInstituicao'])

  return redirect(url_for('logar'))

@app.route("/reset-password", methods=["GET"])
def reset_password_page():
  if not "token" in request.url:
    return redirect(url_for('recuperar_senha'))
  else:
    tokenRecuperacao = request.args.get("token")
    cnx = connect(
      host=getenv("DB_HOST"),
      port=getenv("DB_PORT"),
      user=getenv("DB_USER"),
      password=getenv("DB_PASSW"),
      database=getenv("DB_NAME"))
    cursor = cnx.cursor(buffered=True)
    cursor.execute(f'SELECT Usuarios.email FROM Tokens JOIN Usuarios ON Tokens.idUsuario = Usuarios.idUsuario WHERE Tokens.valorToken = "{tokenRecuperacao}"')
    email = cursor.fetchone()[0]
    if email != "":    
      return render_template("nova_senha.html", token=tokenRecuperacao, email=email)
    else:
       make_response(404)

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
    return redirect(url_for('logar'))

# REST API
@app.route("/api/v1/alterar-senha", methods=["POST"])
def alterar_senha():
   try:
      cnx = connect(
        host=getenv("DB_HOST"),
        port=getenv("DB_PORT"),
        user=getenv("DB_USER"),
        password=getenv("DB_PASSW"),
        database=getenv("DB_NAME"))
      cursor = cnx.cursor(buffered=True)
      novaSenha = request.json["novaSenha"]
      email = request.json["email"]
      cursor.execute(f"SELECT Usuarios.idUsuario, Usuarios.email, Senhas.senha FROM Usuarios JOIN Senhas ON Usuarios.idUsuario = Senhas.passwordOwnerId WHERE Usuarios.email = '{email}';")
      resultados = cursor.fetchall()
      # ta dando erro
      print(resultados)
      senhaAntiga = ""
      for resultado in resultados:
         senhaAntiga = resultado[2]
         idUsuario = resultado[0]
         print(senhaAntiga)
      if senhaAntiga == "":
        return make_response(jsonify({"error": True, "message": "Senha não pode ser em branco."}), 500)
      else:
        cursor.execute(f'UPDATE Senhas SET senha=MD5("{novaSenha}") WHERE (senha = "{senhaAntiga}" AND passwordOwnerId = {idUsuario})')
        cnx.commit()
        cursor.execute(f'DELETE FROM Tokens WHERE idUsuario = {idUsuario}')
        cnx.commit()
        return make_response(jsonify({"success": True, "message": "Senha alterada com sucesso, redirecionado para página de login..."}), 200)
   except Exception as e:
      return make_response(jsonify({"error": True, "message": str(e)}), 500)
@app.route("/api/v1/gerar-recuperacao-de-senha", methods=["POST"])
def gerar_recuperacao_de_senha():  
  try:
      cnx = connect(
          host=getenv("DB_HOST"),
          port=getenv("DB_PORT"),
          user=getenv("DB_USER"),
          password=getenv("DB_PASSW"),
          database=getenv("DB_NAME")
      )
      cursor = cnx.cursor(buffered=True)
      cursor.execute(f'SELECT idUsuario, nomeCompleto FROM Usuarios WHERE email = "{request.json["email"]}"')
      resultados = cursor.fetchall()
      for resultado in resultados:
          idUsuario = resultado[0]
          nomeCompleto = resultado[1]
      
      token_redefinicao = str(uuid.uuid4()).replace("-", "")
      cursor.execute(f'INSERT INTO Tokens (idUsuario, valorToken, dataDeCriacao) VALUES ({idUsuario}, "{token_redefinicao}", NOW())')
      cnx.commit()
      
      email_html = open("./static/mensagem_recovery.html", "r", encoding="utf-8").read()
      message_body = email_html.replace("{placeholderNome}", str(nomeCompleto).upper()).replace("{replaceToken}", token_redefinicao)
      
      msg = MIMEMultipart("alternative")
      msg['From'] = f"Unitask <{getenv('EMAIL_RECUPERACAO_DE_SENHA')}>"
      msg['To'] = request.json["email"]
      msg["Subject"] = "Unitask - Recuperação de Senha"
      msg.add_header('Content-Type', 'text/html;charset=utf-8')
      
      msg.attach(MIMEText(message_body, "html", "utf-8"))
      s.sendmail(msg['From'], [msg['To']], msg.as_string())
      return make_response(jsonify({"success": True, "message": f"E-mail de redefinição de senha enviado para: {str(request.json['email']).lower()}"}))
  except Exception as e:
    print(e)
    return make_response(jsonify({"error": True, "message": str(e)}), 500)

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
    query_register = f'INSERT INTO Usuarios (nomeCompleto, email, instituicaoTipo, cargo) VALUES ("{str(nome).upper()}", "{email}", "{instituicao}", "{cargo}")'
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


@app.route("/api/v1/get-tarefas", methods=["GET"])
def get_tarefas():
  print(session)
  try:
    tarefas = [{}]
    cnx = connect(
      host=getenv("DB_HOST"),
      port=getenv("DB_PORT"),
      user=getenv("DB_USER"),
      password=getenv("DB_PASSW"),
      database=getenv("DB_NAME"))
    cursor = cnx.cursor(buffered=True)
    tarefas = []
    cursor.execute(f'SELECT * FROM Tarefas WHERE idDonoDaTarefa = {session["id"]}')
    responseTarefas = cursor.fetchall()
    for tarefa in responseTarefas:
      if tarefa[5] == 1:
        tarefaConcluida = True
      elif tarefa[5] == 0:
        tarefaConcluida = False
      tarefas.append({"idTarefa": tarefa[0], 
                      "tituloTarefa": tarefa[2], 
                      "descricaoTarefa": tarefa[3], 
                      "dataCriacaoTarefa": tarefa[4], 
                      "tarefaConcluida": tarefaConcluida})
    return make_response(jsonify({"success": True, "tarefas": tarefas}), 200)
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
    idUsuario = session['id']
    if session['id'] == idUsuario:     
      titulo = request.json['titulo']
      descricao = 'Sem descrição' # request.json['descricao']
      cursor.execute(f'INSERT INTO Tarefas (idDonoDaTarefa, tituloTarefa, descricaoTarefa, dataDeCriacao, tarefaConcluida) VALUES ({idUsuario}, "{titulo}", "{descricao}", NOW(), False)')
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
      idUsuario = session['id']
      idTarefa = request.json["idTarefa"]
      if session['id'] == idUsuario:
        cursor.execute(f'UPDATE Tarefas SET tarefaConcluida = 1 WHERE idDonoDaTarefa = {idUsuario} AND idTarefa = {idTarefa};')
        cnx.commit()
        return make_response(jsonify({"success": True, "message": "Tarefa concluída com sucesso!"}), 200)
      else:
         return make_response(jsonify({"error": True, "message": "Você não pode concluir tarefas de outro usuário!"}), 401)
   except Exception as e:
      return make_response(jsonify({"error": True, "message": str(e)}), 500)
   
@app.route("/api/v1/delete-tarefa", methods=["DELETE"])
def delete_tarefa():
   try:
      cnx = connect(
        host=getenv("DB_HOST"),
        port=getenv("DB_PORT"),
        user=getenv("DB_USER"),
        password=getenv("DB_PASSW"),
        database=getenv("DB_NAME"))
      cursor = cnx.cursor(buffered=True)
      idUsuario = session['id']
      idTarefa = request.json['idTarefa']
      if session['id'] == idUsuario:
        cursor.execute(f'DELETE from Tarefas WHERE idDonoDaTarefa = {idUsuario} AND idTarefa = {idTarefa};')
        cnx.commit()
        return make_response(jsonify({"success": True, "message": "Tarefa excluída com sucesso!"}), 200)
      else:
         return make_response(jsonify({"error": True, "message": "Você não pode excluir tarefas de outro usuário!"}), 401)
   except Exception as e:
      return make_response(jsonify({"error": True, "message": str(e)}), 500)

if __name__ in "__main__":
  app.run(host="localhost", port=5000, debug=True)