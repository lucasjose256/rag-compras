import chromadb
import os
from langchain_community.document_loaders import (
    PyPDFDirectoryLoader,
    TextLoader,
    UnstructuredWordDocumentLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from chromadb.utils import embedding_functions  # Importar
from concurrent.futures import ThreadPoolExecutor


class DocumentProcessor:
    def __init__(
        self,
        data_path: str = "data",
        chroma_path: str = "chroma_db",
        collection_name: str = "lei",
        # Padrão, mas configurável
        embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        self.data_path = data_path
        self.chroma_path = chroma_path
        self.collection_name = collection_name
        self.chroma_client = chromadb.PersistentClient(path=self.chroma_path)

        # Configurar a função de embedding
        self.embedding_function = (
            embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=embedding_model_name
            )
        )
        # Ou use outra como OpenAIEmbeddingFunction se preferir e tiver a chave API
        # self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
        # model_name="text-embedding-3-small", api_key="sk-..."
        # )

        self.collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name, embedding_function=self.embedding_function
        )
        self.raw_documents = []
        self.chunks = []

        if not os.path.exists(self.data_path):
            raise FileNotFoundError(
                f"O diretório {self.data_path} não existe.")

    def _load_single_file(self, file_path, loader_class, loader_args=None, loader_kwargs=None):
        """Helper para carregar um único arquivo e lidar com exceções."""
        if loader_args is None:
            loader_args = []
        if loader_kwargs is None:
            loader_kwargs = {}
        try:
            loader = loader_class(file_path, *loader_args, **loader_kwargs)
            docs = loader.load()
            print(
                f"✔️ Carregado com sucesso: {file_path} usando {loader_class.__name__}")
            return docs
        except Exception as e:
            print(
                f"❌ Erro ao carregar {file_path} com {loader_class.__name__}: {e}")
            return []

    def load_documents(self, parallel_loading: bool = True):
        self.raw_documents = []  # Limpar documentos brutos antes de carregar

        # PDF Loader (PyPDFDirectoryLoader carrega todos os PDFs de um diretório)
        pdf_loader = PyPDFDirectoryLoader(self.data_path)
        try:
            pdf_docs = pdf_loader.load()
            if pdf_docs:  # PyPDFDirectoryLoader pode retornar None se não houver PDFs ou erro
                self.raw_documents.extend(pdf_docs)
                print(
                    f"✔️ {len(pdf_docs)} Documentos PDF carregados de {self.data_path}")
            else:
                print(
                    f"ℹ️ Nenhum documento PDF encontrado ou carregado por PyPDFDirectoryLoader em {self.data_path}")
        except Exception as e:
            print(f"❌ Erro ao carregar PDFs com PyPDFDirectoryLoader: {e}")

        # Configurar para outros tipos de arquivo
        file_paths_to_load = []
        for file_name in os.listdir(self.data_path):
            file_path = os.path.join(self.data_path, file_name)
            if not os.path.isfile(file_path):  # Ignorar subdiretórios aqui
                continue

            if file_name.endswith(".txt"):
                file_paths_to_load.append(
                    (file_path, TextLoader, [], {"encoding": "utf-8"})
                )
            elif file_name.endswith(".docx"):
                file_paths_to_load.append(
                    (file_path, UnstructuredWordDocumentLoader, [], {})
                )
            # Adicione outros tipos de arquivo aqui se necessário

        # Se nem PDFs nem outros arquivos foram encontrados
        if not file_paths_to_load and not self.raw_documents:
            raise ValueError(
                f"Nenhum arquivo suportado (PDF, TXT, DOCX) encontrado em {self.data_path}.")

        if parallel_loading and file_paths_to_load:
            with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
                future_docs = [
                    executor.submit(self._load_single_file, fp, lc, la, lk)
                    for fp, lc, la, lk in file_paths_to_load
                ]
                for future in future_docs:
                    self.raw_documents.extend(future.result())
        elif file_paths_to_load:  # Carregamento sequencial se parallel_loading for False
            for fp, lc, la, lk in file_paths_to_load:
                self.raw_documents.extend(
                    self._load_single_file(fp, lc, la, lk))

        if not self.raw_documents:
            # Se raw_documents ainda estiver vazio após todas as tentativas
            print(
                "⚠️ Nenhum documento foi carregado com sucesso. Verifique os logs de erro.")
            # Você pode querer levantar um ValueError aqui ou permitir que o fluxo continue
            # dependendo se ter documentos é absolutamente crítico para os próximos passos.
            # raise ValueError("Nenhum documento foi carregado com sucesso.")
            return  # Retorna para evitar erro no split de lista vazia

        print(f"📄 Total de documentos carregados: {len(self.raw_documents)}")

    def split_documents(self, chunk_size=400, chunk_overlap=100):
        if not self.raw_documents:
            print("ℹ️ Nenhum documento para dividir.")
            self.chunks = []
            return

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
        self.chunks = splitter.split_documents(self.raw_documents)
        print(f"🔗 Total de chunks gerados: {len(self.chunks)}")

    def save_to_chroma(self):
        if not self.chunks:
            print("ℹ️ Nenhum chunk para salvar no ChromaDB.")
            return

        documents = [chunk.page_content for chunk in self.chunks]
        metadata = [
            {
                "source": chunk.metadata.get("source", "desconhecido"),
                # Exemplo de metadado adicional
                "page": chunk.metadata.get("page", -1),
                "file_type": os.path.splitext(chunk.metadata.get("source", ""))[1]
                or "unknown",
            }
            for chunk in self.chunks
        ]
        # Garante IDs únicos
        ids = [f"ID_{i}" for i in range(len(self.chunks))]

        try:
            # Se a coleção já tiver dados e você quiser apenas adicionar/atualizar:
            # self.collection.upsert(documents=documents, metadatas=metadata, ids=ids)
            # Se você quiser limpar e adicionar (CUIDADO: apaga dados existentes na coleção!):
            # self.chroma_client.delete_collection(name=self.collection_name)
            # self.collection = self.chroma_client.create_collection(
            # name=self.collection_name, embedding_function=self.embedding_function
            # )
            # self.collection.add(documents=documents, metadatas=metadata, ids=ids)

            # Upsert é geralmente mais seguro e flexível
            self.collection.upsert(documents=documents,
                                   metadatas=metadata, ids=ids)
            print(
                f"✅ {len(documents)} chunks processados no ChromaDB na coleção '{self.collection_name}' com sucesso!"
            )
        except Exception as e:
            print(f"❌ Erro ao salvar no ChromaDB: {e}")

    def get_collection_count(self):
        count = self.collection.count()
        print(f"📦 Total de itens na coleção '{self.collection_name}': {count}")
        return count

    def process_and_store(self, chunk_size=400, chunk_overlap=100, parallel_loading=True):
        """Executa todo o pipeline de processamento e armazenamento."""
        self.load_documents(parallel_loading=parallel_loading)
        if self.raw_documents:  # Só prossegue se documentos foram carregados
            self.split_documents(chunk_size=chunk_size,
                                 chunk_overlap=chunk_overlap)
            self.save_to_chroma()
        self.get_collection_count()


# 🚀 Executando
if __name__ == "__main__":
    # Crie diretórios de exemplo se não existirem
    if not os.path.exists("data"):
        os.makedirs("data")
    if not os.path.exists("chroma_db"):
        os.makedirs("chroma_db")

    # Adicione alguns arquivos de exemplo em 'data/'
    # Ex: data/doc1.txt, data/doc2.pdf, data/doc3.docx

    # Exemplo de uso com um modelo de embedding multilíngue mais leve
    processor = DocumentProcessor(
        data_path="data",
        chroma_path="chroma_db",
        collection_name="minha_colecao_leis",
        embedding_model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    processor.process_and_store(chunk_size=500, chunk_overlap=150)

    # # Para testar a recuperação (exemplo básico)
    # if processor.get_collection_count() > 0:
    #     try:
    #         results = processor.collection.query(
    #             query_texts=["qual é a lei sobre X?"],  # Sua pergunta aqui
    #             n_results=3
    #         )
    #         print("\nResultados da busca de exemplo:")
    #         for i, doc in enumerate(results.get("documents", [])):
    #             print(f"Resultado {i+1}:")
    #             # Mostra apenas os primeiros 150 caracteres do documento
    #             print(doc[0][:150] + "..." if doc else "N/A")
    #             print(f"Metadados: {results.get('metadatas', [])[0][i]}")
    #             print("-" * 20)
    #     except Exception as e:
    #         print(f"Erro ao fazer query: {e}")
