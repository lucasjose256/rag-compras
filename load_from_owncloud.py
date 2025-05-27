from webdav3.client import Client

options = {
    'webdav_hostname': "https://<seu_dominio>/remote.php/dav/files/<usuario>/",
    'webdav_login': "<seu_usuario>",
    'webdav_password': "<sua_senha_ou_token>"
}

client = Client(options)

remote_dir = '/caminho/para/o/diretorio/'

files = client.list(remote_dir)

# Filtra apenas arquivos (remove o próprio diretório e subdiretórios, se quiser)
for file in files:
    if file == remote_dir:
        continue  # Ignora o diretório raiz
    print(f"Baixando: {file}")

    # Define o nome local para salvar o arquivo
    local_filename = file.split('/')[-1]

    # Faz o download
    client.download_sync(remote_path=file, local_path=local_filename)

print("Todos os arquivos foram baixados com sucesso.")
