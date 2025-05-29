from webdav3.client import Client

options = {
    'webdav_hostname': "https://<seu_dominio>/remote.php/dav/files/<usuario>/",
    'webdav_login': "xxxxxx",
    'webdav_password': "xxxxxx"
}

client = Client(options)

remote_dir = '/caminho/para/o/diretorio/'

files = client.list(remote_dir)


for file in files:
    if file == remote_dir:
        continue  
    print(f"Baixando: {file}")


    local_filename = file.split('/')[-1]

    client.download_sync(remote_path=file, local_path=local_filename)

print("Todos os arquivos foram baixados com sucesso.")
