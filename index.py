from flask import Flask, render_template, request
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES, PKCS1_OAEP
import secrets
from pathlib import Path
from os import getenv, listdir

i = 0
for file in listdir():
    if file.endswith(".pem"): i += 1
if i != 2:
    key = RSA.generate(2048)
    private_key = key.export_key()
    with open(getenv("namePrivate"), "wb") as file_out:
        file_out.write(private_key)

    public_key = key.publickey().export_key()
    with open(getenv("namePublic"), "wb") as file_out:
        file_out.write(public_key)
del i

if getenv("myHouse"):
    from dotenv import load_dotenv
    load_dotenv()

PATH_CODES = Path(__name__).parent / getenv("mypath")

app = Flask(__name__)

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

    ciphertext, tag = cipher_aes.encrypt_and_digest(lang.encode()+b';;'+data)
    url = secrets.token_urlsafe(20)
    with open(PATH_CODES / f"{url}.bin", "wb") as file:
        [ file.write(x) for x in (enc_session_key, cipher_aes.nonce, tag, ciphertext) ]
    return {"msg": "subido con exito", "code-code":url}

@app.get("/momento/<string:code>")
def momento(code):
    file_in = open(PATH_CODES / f"{code}.bin", "rb")

    private = getenv("namePrivate").encode()
    print(private)
    private_key = RSA.import_key(private)
    private.close()

    enc_session_key, nonce, tag, ciphertext = [ file_in.read(x) for x in (private_key.size_in_bytes(), 16, 16, -1) ]

    cipher_rsa = PKCS1_OAEP.new(private_key)
    session_key = cipher_rsa.decrypt(enc_session_key)

    cipher_aes = AES.new(session_key, AES.MODE_EAX, nonce)
    data = cipher_aes.decrypt_and_verify(ciphertext, tag)
    data = data.decode("utf-8")
    lang, data = data.split(";;")
    return render_template("momento.html", code = data, language = lang)

if __name__ == '__main__':
    app.run(debug = getenv("myHouse"))