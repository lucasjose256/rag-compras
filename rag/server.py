from dotenv import load_dotenv
from flask import Flask, request, Response, jsonify  # Adicionado Response
from flask_cors import CORS
import google.generativeai as genai
import os


load_dotenv()

app = Flask(__name__)
CORS(app)
# Em app.py
import traceback 
from document_processor import DocumentProcessor
DATA_DIR = "data"
CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "utfpr"
processor = DocumentProcessor(
        data_path=DATA_DIR,
        chroma_path=CHROMA_DIR,
        collection_name=COLLECTION_NAME
    )
@app.route('/chat', methods=['POST'])
def chat_stream():
    data = request.get_json()
    user_message = data.get('message')

    if not user_message:
        return jsonify({"error": "Nenhuma mensagem recebida."}), 400

    print(f"Mensagem recebida para streaming: {user_message}")
    # Retorna uma Resposta de streaming. text/plain é simples, mas você pode usar text/event-stream para SSE.
    # Para text/plain, o cliente precisa saber como lidar com os chunks.
    
   
    return  processor.query_async(user_message)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
