from flask import Flask
from threading import Thread
from config import TOKEN, CLIENT_SECRET
import asyncio

app = Flask(__name__)
app.config["SECRET_KEY"] = "verysecret" #Nothing to see here#
client_secret=(CLIENT_SECRET)

  
@app.route('/')
def main():
  print("Website pinged!")

  return "Your Bot Is Ready"



def run():
  app.run(host="0.0.0.0", port=8000)
def keep_alive():
  server = Thread(target=run)
  server.start()