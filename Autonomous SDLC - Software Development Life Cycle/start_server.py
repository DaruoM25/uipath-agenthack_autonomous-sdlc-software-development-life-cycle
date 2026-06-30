import subprocess
import sys
import time
import os
from dotenv import load_dotenv

def start_server_and_ngrok():
    # Charger les variables d'environnement depuis le fichier .env
    load_dotenv()
    ngrok_token = os.getenv("NGROK_TOKEN", "")
    
    # Préparer l'environnement pour ngrok et FastAPI
    env = os.environ.copy()
    if ngrok_token:
        env["NGROK_AUTHTOKEN"] = ngrok_token
        
    public_url = "https://observant-driven-scrooge.ngrok-free.dev"
    env["NGROK_PUBLIC_URL"] = public_url

    print("🚀 Démarrage du serveur FastAPI et du tunnel Ngrok...")
    
    # Tuer tout processus ngrok résiduel pour éviter l'erreur "already online"
    subprocess.run(["taskkill", "/F", "/IM", "ngrok.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2) # Laisser le temps au cloud ngrok de libérer le domaine
    
    # 1. Démarrer Ngrok
    ngrok_cmd = ["ngrok", "http", "--url=observant-driven-scrooge.ngrok-free.dev", "8000"]
    ngrok_process = subprocess.Popen(ngrok_cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    time.sleep(4) # Attendre l'ouverture du tunnel
    
    # 2. Récupérer l'URL Ngrok via son API locale
    import urllib.request
    import json
    import re
    
    public_url = "https://observant-driven-scrooge.ngrok-free.dev"
    try:
        req = urllib.request.Request("http://127.0.0.1:4040/api/tunnels")
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            public_url = data['tunnels'][0]['public_url']
            print(f"Ngrok Tunnel URL retrieved: {public_url}")
    except Exception as e:
        print(f"Failed to fetch Ngrok URL from API, using default. Error: {e}")
        
    env["NGROK_PUBLIC_URL"] = public_url

    # 3. Injecter l'URL dans Main.xaml
    main_xaml_path = r"C:\DEVPOST.Hackathon\UiPath AgentHack\UiPath\Orchestrateur_Final\Main.xaml"
    if os.path.exists(main_xaml_path):
        with open(main_xaml_path, "r", encoding="utf-8") as f:
            xaml_content = f.read()
            
        new_content = re.sub(
            r'(<Variable x:TypeArguments="x:String" Name="strBaseUrl">[\s\S]*?<Literal x:TypeArguments="x:String">)(.*?)(</Literal>)',
            rf'\g<1>{public_url}\g<3>',
            xaml_content,
            count=1
        )
        
        with open(main_xaml_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("Updated Main.xaml with the new Base URL.")
    
    # 4. Démarrer Uvicorn
    uvicorn_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        env=env
    )
    
    time.sleep(2) # Attendre que le serveur commence son démarrage
    
    try:
        print("\n✅ Système en ligne ! Appuyez sur CTRL+C pour tout arrêter.")
        
        # Garder le script en vie
        uvicorn_process.wait()
        
    except FileNotFoundError:
        print("❌ ERREUR : 'ngrok' n'est pas reconnu en tant que commande interne.")
        print("Veuillez installer Ngrok ou ajouter ngrok.exe à vos variables d'environnement (PATH).")
        uvicorn_process.terminate()
    except KeyboardInterrupt:
        print("\n🛑 Arrêt en cours...")
        uvicorn_process.terminate()
        if 'ngrok_process' in locals():
            ngrok_process.terminate()
        print("✅ Tout a été arrêté correctement.")

if __name__ == "__main__":
    start_server_and_ngrok()
