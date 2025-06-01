import os
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from langchain_community.document_loaders import (
    PyPDFDirectoryLoader,
    TextLoader,
    UnstructuredWordDocumentLoader,
)
import google.generativeai as genai
from langchain_text_splitters import RecursiveCharacterTextSplitter


class DocumentProcessor:
    """
    Classe para processar documentos, gerar embeddings e armazenar no ChromaDB.
    """

    def __init__(self, data_path: str, chroma_path: str, collection_name: str = "lei"):

        load_dotenv()

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "A chave da API 'GEMINI_API_KEY' não foi encontrada. Verifique o arquivo .env.")

        genai.configure(api_key=api_key)
        self.data_path = data_path
        self.chroma_path = chroma_path
        self.collection_name = collection_name

        if not os.path.exists(self.data_path):
            raise FileNotFoundError(
                f"O diretório de dados {self.data_path} não existe.")

        # Função de embedding
        embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

        # Cliente e coleção do ChromaDB
        self.chroma_client = chromadb.PersistentClient(path=self.chroma_path)
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=embedding_function
        )

        print(
            f"ChromaDB inicializado. Coleção '{self.collection_name}' pronta em '{self.chroma_path}'.")

    def _load_raw_documents(self) -> list:
        """
        Carrega documentos do diretório.

        Retorna:
            list: Lista de objetos Document.
        """
        loaders = []
        raw_documents = []

        pdf_files_exist = any(file.endswith(".pdf")
                              for file in os.listdir(self.data_path))
        if pdf_files_exist:
            loaders.append(PyPDFDirectoryLoader(self.data_path))
        else:
            print(f"Nenhum arquivo PDF encontrado em {self.data_path}.")

        for file_name in os.listdir(self.data_path):
            file_path = os.path.join(self.data_path, file_name)
            if file_name.endswith(".txt"):
                loaders.append(TextLoader(file_path, encoding="utf-8"))
            elif file_name.endswith(".docx"):
                loaders.append(UnstructuredWordDocumentLoader(file_path))

        if not loaders:
            print(
                f"Nenhum loader configurado. Verifique os arquivos em {self.data_path}.")
            return []

        for loader in loaders:
            try:
                print(
                    f"Carregando documentos com: {loader.__class__.__name__}")
                raw_documents.extend(loader.load())
            except Exception as e:
                print(f"Erro ao carregar com {loader.__class__.__name__}: {e}")

        print(f"Total de {len(raw_documents)} documentos carregados.")
        return raw_documents

    def _split_documents(self, raw_documents: list, chunk_size: int = 400, chunk_overlap: int = 100) -> list:
        """
        Divide documentos em chunks menores.

        Args:
            raw_documents (list): Lista de documentos carregados.
            chunk_size (int): Tamanho máximo dos chunks.
            chunk_overlap (int): Sobreposição entre os chunks.

        Retorna:
            list: Lista de chunks.
        """
        if not raw_documents:
            print("Nenhum documento para dividir.")
            return []

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len
        )
        chunks = text_splitter.split_documents(raw_documents)
        print(f"{len(chunks)} chunks criados.")
        return chunks

    def process_and_ingest_documents(self, chunk_size: int = 400, chunk_overlap: int = 100):
        """
        Processa os documentos e injeta no ChromaDB.
        """
        raw_documents = self._load_raw_documents()
        if not raw_documents:
            print("Nenhum documento carregado. Processo encerrado.")
            return

        chunks = self._split_documents(
            raw_documents, chunk_size, chunk_overlap)
        if not chunks:
            print("Nenhum chunk criado. Processo encerrado.")
            return

        documents_to_ingest = [chunk.page_content for chunk in chunks]

        metadatas_to_ingest = []
        for chunk in chunks:
            source = chunk.metadata.get("source", "desconhecido")
            file_type = os.path.splitext(
                source)[1] if source != "desconhecido" else "unknown"
            metadata_entry = {
                "source": str(source),
                "file_type": str(file_type)
            }
            metadatas_to_ingest.append(metadata_entry)

        ids_to_ingest = [f"ID{i}" for i in range(len(chunks))]

        try:
            self.collection.add(
                documents=documents_to_ingest,
                metadatas=metadatas_to_ingest,
                ids=ids_to_ingest
            )
            print(
                f"{len(documents_to_ingest)} chunks adicionados na coleção '{self.collection_name}'.")
        except Exception as e:
            print(f"Erro ao salvar no ChromaDB: {e}")

    def get_collection_count(self) -> int:
        """
        Retorna o número de itens na coleção.

        Retorna:
            int: Contagem de itens.
        """
        count = self.collection.count()
        print(f"Total de itens na coleção '{self.collection_name}': {count}")
        return count

    def query(self,  n_results: int = 6):
        
        model = genai.GenerativeModel('gemini-1.5-flash') # ou 'gemini-1.5-pro-latest', 'gemini-pro'
        while True:
            user_query = input(
                "\nQual é a sua pergunta? (ou digite 's' para encerrar)\n\n")

            if user_query.lower() == "s":
                print("Encerrando o chat...")
                break
            """
        Faz uma consulta na coleção.

        Args:
            query_text (str): Texto da consulta.
            n_results (int): Número de resultados a retornar.

        Retorna:
            list: Lista de documentos e metadados encontrados.
        """
            results = self.collection.query(
                query_texts=[user_query],
                n_results=n_results
            )
            # print("\nResultados da consulta:")
            # for i, doc in enumerate(results['documents'][0]):
            #     print(f"Resultado {i+1}: {doc}")
            #     if results['metadatas'] and results['metadatas'][0] and len(results['metadatas'][0]) > i:
            #         print(f"  Metadados: {results['metadatas'][0][i]}")
            #     print("-" * 20)
            system_prompt = f"""
            Você é um assistente especializado em responder perguntas com base nos dados fornecidos.  
            Sua missão é utilizar ao máximo as informações disponíveis, inferindo respostas sempre que possível, sem inventar ou recorrer a conhecimento externo.  

            **Regras para suas respostas:**  
            - Se houver informações suficientes, responda de forma **clara, direta e objetiva**.  
            - Se as informações forem **parciais**, tente **inferir** a melhor resposta possível, explicando sua lógica.  
            - Se não houver **dados suficientes**, seja honesto e responda apenas: `"Não sei com certeza, mas com base no contexto, posso inferir que..."` ou `"Não tenho informações suficientes para responder com precisão."`  
            - **Nunca invente fatos** ou forneça respostas baseadas em suposições sem justificativa.  

            🔍 **Contexto disponível:**  
            {str(results['documents'])}
            """

            prompt = f"{system_prompt}\n\nUsuário: {user_query}"

           # response = model.generate_content(prompt, stream=True)

        #    print("\nResposta do Assistente:")
            full_response_text = ""
            try:
                # Use stream=True para obter a resposta em partes
                response_stream = model.generate_content(prompt, stream=True)

                for chunk in response_stream:
                    if chunk.text: # Verifica se o chunk tem texto
                        print(chunk.text, end="", flush=True) # Imprime o texto do chunk sem nova linha e força a saída
                        full_response_text += chunk.text
            except Exception as e:
                print(f"\nOcorreu um erro ao gerar a resposta: {e}")
                # Você pode querer lidar com diferentes tipos de erros aqui,
                # como google.generativeai.types.BlockedPromptException

            print("\n\n---------------------\n")
            # O return original era response.text. Com streaming, você constrói o texto completo.
            # Se você ainda precisa retornar o texto completo, use full_response_text
            # return full_response_text # Descomente se precisar retornar o texto completo

            return None



        # --- Exemplo de uso ---
if __name__ == "__main__":
    DATA_DIR = "data"
    CHROMA_DIR = "chroma_db"
    COLLECTION_NAME = "utfpr"

    try:
        processor = DocumentProcessor(
            data_path=DATA_DIR,
            chroma_path=CHROMA_DIR,
            collection_name=COLLECTION_NAME
        )

        processor.process_and_ingest_documents()
        processor.get_collection_count()

        # Faz uma consulta de exemplo
        if processor.get_collection_count() > 0:
            processor.query()

    except FileNotFoundError as e:
        print(f"Erro de configuração: {e}")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")
