from dotenv import load_dotenv
from flask import Flask, request, Response, jsonify  # Adicionado Response
from flask_cors import CORS
import google.generativeai as genai
import os


load_dotenv()
# --- Configuração do Gemini (coloque no início do seu app.py) ---
# Idealmente, configure a API Key via variável de ambiente
try:
    GEMINI_API_KEY = os.environ['GEMINI_API_KEY']
    genai.configure(api_key=GEMINI_API_KEY)
except KeyError:
    print("ERRO: Variável de ambiente GOOGLE_API_KEY não configurada!")
    # Você pode pedir a chave aqui para teste, mas NÃO FAÇA ISSO EM PRODUÇÃO
    # GOOGLE_API_KEY = input("Por favor, insira sua GOOGLE_API_KEY: ")
    # if not GOOGLE_API_KEY:
    #     exit("Chave de API não fornecida. Encerrando.")
    # genai.configure(api_key=GOOGLE_API_KEY)
    exit("Chave API não configurada.")


# --- Simulação da sua coleção ChromaDB e DocumentProcessor ---
# No seu projeto real, você instanciaria seu DocumentProcessor aqui
# e o usaria dentro da função de streaming.
class MockCollection:
    def query(self, query_texts, n_results):
        user_query = query_texts[0].lower()
        print(f"[MockCollection] Consultando para: '{user_query}'")
        if "capital da frança" in user_query:
            return {
                'documents': [['Paris é a capital e a cidade mais populosa da França.',
                               'A França está localizada na Europa Ocidental.']],
                'metadatas': [[{'source': 'doc_A.txt'}, {'source': 'doc_B.txt'}]]
            }
        elif "python" in user_query:
            return {
                'documents': [['Python é uma linguagem de programação versátil e popular.',
                               'É conhecida por sua sintaxe clara e legível.']],
                'metadatas': [[{'source': 'python_intro.md'}, {'source': 'python_docs.pdf'}]]
            }
        else:
            return {
                'documents': [[f"Informações contextuais sobre '{user_query}' seriam recuperadas aqui."]],
                'metadatas': [[{'source': 'placeholder.txt'}]]
            }


# Instância simulada da coleção. Substitua pela sua real.
mock_chroma_collection = MockCollection()
# -----------------------------------------------------------------

app = Flask(__name__)
CORS(app)
# Em app.py
import traceback 

# ... (resto do seu código Flask) ...

def generate_streaming_response(user_query_text: str):
    try:
        print(f"[GENERATOR] Iniciando para query: '{user_query_text}'")
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # ... (sua lógica RAG para obter rag_results e prompt) ...
        # Cole sua lógica RAG e construção do prompt aqui, como antes
        # Exemplo simplificado para garantir que o prompt exista:
        n_results = 2
        rag_results = mock_chroma_collection.query(
            query_texts=[user_query_text],
            n_results=n_results
        )
        documentos_formatados = ""
        if rag_results and rag_results.get('documents') and rag_results['documents'][0]:
            for i, doc_text in enumerate(rag_results['documents'][0]):
                documentos_formatados += f"\n--- Documento {i+1} ---\n{doc_text}\n"
                if rag_results.get('metadatas') and rag_results['metadatas'][0] and \
                   len(rag_results['metadatas'][0]) > i and rag_results['metadatas'][0][i]:
                    metadata = rag_results['metadatas'][0][i]
                    documentos_formatados += f"Metadados: {str(metadata)}\n"
        else:
            documentos_formatados = "Nenhum documento relevante encontrado.\n"

        system_prompt = f"""
Você é um assistente especializado em responder perguntas com base nos dados fornecidos.
Sua missão é utilizar ao máximo as informações disponíveis, inferindo respostas sempre que possível, sem inventar ou recorrer a conhecimento externo.
🔍 **Contexto disponível:**
{documentos_formatados}
--- Fim do Contexto ---
"""
        prompt = f"{system_prompt}\n\nUsuário: {user_query_text}\n\nAssistente:"
        # Fim da lógica RAG e prompt


        print(f"[GENERATOR] Gerando conteúdo com Gemini para o prompt...")
        response_stream = model.generate_content(prompt, stream=True)

        chunk_count = 0
        for chunk in response_stream:
            chunk_count += 1
            if chunk.text:
                print(f"[GENERATOR] Enviando chunk {chunk_count}: '{chunk.text[:50]}...'") # Log do chunk
                yield chunk.text
            else:
                print(f"[GENERATOR] Chunk {chunk_count} sem texto.")
        
        if chunk_count == 0:
            print("[GENERATOR] Nenhum chunk foi gerado pelo Gemini.")
            yield "Desculpe, não consegui gerar uma resposta no momento." # Fallback se nada for gerado
        else:
            print(f"[GENERATOR] Streaming finalizado. Total de chunks com texto: {chunk_count_com_texto}") # Ajustar se necessário

    except genai.types.generation_types.BlockedPromptException as bpe:
        print(f"[GENERATOR ERROR] Prompt bloqueado: {bpe}")
        print(traceback.format_exc())
        yield "Desculpe, sua pergunta foi bloqueada pelas políticas de conteúdo."
    except Exception as e:
        print(f"[GENERATOR ERROR] Erro inesperado: {e}")
        print(traceback.format_exc()) # Isso imprimirá o stack trace completo no console do Flask
        yield "Ocorreu um erro interno ao tentar processar sua solicitação."

@app.route('/chat', methods=['POST'])
def chat_stream():
    data = request.get_json()
    user_message = data.get('message')

    if not user_message:
        return jsonify({"error": "Nenhuma mensagem recebida."}), 400

    print(f"Mensagem recebida para streaming: {user_message}")
    # Retorna uma Resposta de streaming. text/plain é simples, mas você pode usar text/event-stream para SSE.
    # Para text/plain, o cliente precisa saber como lidar com os chunks.
    return Response(generate_streaming_response(user_message), mimetype='text/plain; charset=utf-8')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
