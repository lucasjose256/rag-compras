from main import DocumentProcessor


if __name__ == "__main__":
    DATA_DIR = "data"
    CHROMA_DIR = "chroma_db"
    COLLECTION_NAME = "utfpr"
    processor = DocumentProcessor(
            data_path=DATA_DIR,
            chroma_path=CHROMA_DIR,
            collection_name=COLLECTION_NAME
        )
    processor.query("compras")
      