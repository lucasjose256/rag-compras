from langchain_community.document_loaders import (
    PyPDFDirectoryLoader,
    TextLoader,
    CSVLoader,
    UnstructuredWordDocumentLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
import chromadb
import os


class DocumentProcessor:
    
    def __init__(self, data_path: str = "data", chroma_path: str = "chroma_db"):
        self.data_path = data_path
        self.chroma_path = chroma_path
        self.chroma_client = chromadb.PersistentClient(path=self.chroma_path)
        self.collection = self.chroma_client.get_or_create_collection(name="lei")
        self.raw_documents = []
        self.chunks = []

        if not os.path.exists(self.data_path):
            raise FileNotFoundError(f"O diretório {self.data_path} não existe.")

    def load_documents(self):
        loaders = self._configure_loaders()

        for loader in loaders:
            try:
                docs = loader.load()
                self.raw_documents.extend(docs)
                print(f"✔️ Carregado com sucesso: {loader}")
            except Exception as e:
                print(f"❌ Erro ao carregar com {loader}: {e}")

        if not self.raw_documents:
            raise ValueError("Nenhum documento foi carregado.")

        print(f"📄 Total de documentos carregados: {len(self.raw_documents)}")

    def split_documents(self, chunk_size=400, chunk_overlap=100):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
        self.chunks = splitter.split_documents(self.raw_documents)
        print(f"🔗 Total de chunks gerados: {len(self.chunks)}")

    def save_to_chroma(self):
        documents = [chunk.page_content for chunk in self.chunks]
        metadata = [
            {
                "source": chunk.metadata.get("source", "desconhecido"),
                "file_type": os.path.splitext(chunk.metadata.get("source", ""))[1]
                or "unknown",
            }
            for chunk in self.chunks
        ]
        ids = [f"ID{i}" for i in range(len(self.chunks))]

        try:
            self.collection.upsert(documents=documents, metadatas=metadata, ids=ids)
            print(
                f"✅ {len(documents)} chunks carregados no ChromaDB com sucesso!"
            )
        except Exception as e:
            print(f"❌ Erro ao salvar no ChromaDB: {e}")

    def get_collection_count(self):
        count = self.collection.count()
        print(f"📦 Total de itens na coleção 'lei': {count}")
        return count

    def _configure_loaders(self):
        loaders = []

        # PDF
        loaders.append(PyPDFDirectoryLoader(self.data_path))

        # TXT
        for file in os.listdir(self.data_path):
            if file.endswith(".txt"):
                loaders.append(TextLoader(os.path.join(self.data_path, file), encoding="utf-8"))

        # DOCX
        for file in os.listdir(self.data_path):
            if file.endswith(".docx"):
                loaders.append(UnstructuredWordDocumentLoader(os.path.join(self.data_path, file)))


        return loaders


# 🚀 Executando
if __name__ == "__main__":
    processor = DocumentProcessor(data_path="data", chroma_path="chroma_db")
    processor.load_documents()
    processor.split_documents(chunk_size=400, chunk_overlap=100)
    processor.save_to_chroma()
    processor.get_collection_count()
