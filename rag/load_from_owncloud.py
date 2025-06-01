import os
from owncloud import Client

oc = Client('https://nuvem.utfpr.edu.br')
oc.login('user', 'senha')

folder_path = '/Estagiários/IA-compras'

local_download_folder = r'C:\Users\lucas\Documents\Python\rag-compras\data'
os.makedirs(local_download_folder, exist_ok=True)

files = oc.list(folder_path)

for f in files:
    if not f.is_dir():
        print(f.name)
        local_file = os.path.join(local_download_folder, f.name)
        

        if os.path.exists(local_file):
            print(f"⚠ Já existe: {f.name}, pulando...")
            continue
    
        oc.get_file(folder_path + '/' + f.name, local_file)
        print(f"✔ Baixado: {f.name}")
