from flask import Flask, render_template, request
from flask_mysqldb import MySQL
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES, PKCS1_OAEP
import secrets
from uuid import uuid4
import io
from os import getenv

if getenv("myHouse"):
    from dotenv import load_dotenv
    load_dotenv()

app = Flask(__name__)
app.config["MYSQL_HOST"] = getenv("BD_HOST")
app.config["MYSQL_USER"] = getenv("BD_USER")
app.config["MYSQL_PASSWORD"] = getenv("BD_PASS")
app.config["MYSQL_DB"] = getenv("BD_NAME")

mysql = MySQL(app)

@app.get("/")
@app.get("/momento")
def index():
    return render_template("index.html")

@app.post("/upload")
def upload():
    data = request.files.get("code").stream.read().strip()
    if not data: return {"status": False, "msg": "No puede subir un archivo vacio"}
    lang = request.form.get("lang").strip()

    public = open(getenv("namePublic"))
    recipient_key = RSA.import_key(public.read())
    session_key = get_random_bytes(16)
    public.close()

    cipher_rsa = PKCS1_OAEP.new(recipient_key)
    enc_session_key = cipher_rsa.encrypt(session_key)
    cipher_aes = AES.new(session_key, AES.MODE_EAX)

    ciphertext, tag = cipher_aes.encrypt_and_digest(data)
    url = secrets.token_urlsafe(20)
    content = b''.join( x for x in (enc_session_key, cipher_aes.nonce, tag, ciphertext) )
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO momentos (uuid, content, url, lang) VALUES (%s, %b, %s, %s)", (f"{uuid4()}", content, url, lang))
    mysql.connection.commit()
    cur.close()
    return {"msg": "subido con exito", "code-code":url}

@app.get("/momento/<string:code>")
def momento(code):
    cur = mysql.connection.cursor()
    cur.execute("SELECT content, lang FROM momentos WHERE url = %s", (code, ))
    content, lang = cur.fetchall()[0]
    file_in = io.BytesIO(content)

    cur.execute(f"SELECT {getenv('namePrivate')} FROM {getenv('tablePrivate')}")
    res:bytes = cur.fetchall()[0][0]
    private = io.StringIO(res.decode())
    private_key = RSA.import_key(private.read())
    cur.close()

    enc_session_key, nonce, tag, ciphertext = [ file_in.read(x) for x in (private_key.size_in_bytes(), 16, 16, -1) ]

    cipher_rsa = PKCS1_OAEP.new(private_key)
    session_key = cipher_rsa.decrypt(enc_session_key)

    cipher_aes = AES.new(session_key, AES.MODE_EAX, nonce)
    data = cipher_aes.decrypt_and_verify(ciphertext, tag)
    return render_template("momento.html", code = data.decode("utf-8"), language = lang)

if __name__ == '__main__':
    app.run(debug = getenv("myHouse"))