import subprocess
import time
import sys
import os
import glob
from dotenv import load_dotenv

def main():
    print("Starting FastAPI server and Ngrok...")
    
    # Charger l'environnement
    load_dotenv()
    ngrok_token = os.getenv("NGROK_TOKEN", "")
    env = os.environ.copy()
    if ngrok_token:
        env["NGROK_AUTHTOKEN"] = ngrok_token
    # 2. Démarrer Ngrok (sans domaine fixe pour qu'il prenne n'importe lequel si besoin, ou avec le domaine si spécifié)
    ngrok_cmd = ["ngrok", "http", "8000"]
    # Si on veut forcer le domaine, on peut le garder, mais ici on le laisse dynamique ou on garde le fixe
    ngrok_cmd = ["ngrok", "http", "--url=observant-driven-scrooge.ngrok-free.dev", "8000"]
    ngrok_process = subprocess.Popen(ngrok_cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    time.sleep(4) # Attendre que Ngrok démarre et ouvre le tunnel
    
    # 3. Récupérer l'URL Ngrok via son API locale
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

    # 4. Injecter l'URL dans Main.xaml
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
        
    # 5. Démarrer FastAPI
    app_dir = r"c:\DEVPOST.Hackathon\UiPath AgentHack\Autonomous SDLC - Software Development Life Cycle"
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=app_dir,
        env=env
    )
    time.sleep(3) # Wait for server to start
    
    uipath_robot_paths = [
        r"C:\Users\Administrateur\AppData\Local\Programs\UiPathPlatform\Studio\26.0.196-cloud.23786\UiRobot.exe",
        r"C:\Program Files\UiPath\Studio\UiRobot.exe",
        os.path.expandvars(r"%LocalAppData%\Programs\UiPath\Studio\UiRobot.exe"),
        r"C:\Users\WDAGUtilityAccount\AppData\Local\Programs\UiPath\Studio\UiRobot.exe",
        r"C:\Users\Administrateur\AppData\Local\Programs\UiPath\Studio\UiRobot.exe"
    ]
    
    robot_path = None
    for p in uipath_robot_paths:
        if os.path.exists(p):
            robot_path = p
            break
            
    project_json_path = r"C:\DEVPOST.Hackathon\UiPath AgentHack\UiPath\Orchestrateur_Final\project.json"
    pkg_out_dir = r"C:\DEVPOST.Hackathon\UiPath AgentHack\UiPath\pkg_out"
    
    studio_cli_path = robot_path.replace("UiRobot.exe", "UiPath.Studio.CommandLine.exe")
    
    import glob
    import shutil
    
    try:
        os.makedirs(pkg_out_dir, exist_ok=True)
            
            
        print(f"Publishing UiPath Project using {studio_cli_path}...", flush=True)
        try:
            pub_result = subprocess.run([studio_cli_path, "publish", "-p", project_json_path, "-f", pkg_out_dir], capture_output=True, text=True, timeout=120)
            print("Publish Output:", flush=True)
            print(pub_result.stdout, flush=True)
            print(pub_result.stderr, flush=True)
        except subprocess.TimeoutExpired as e:
            print("Publishing timed out!", flush=True)
            if e.stdout: print(e.stdout, flush=True)
            if e.stderr: print(e.stderr, flush=True)
        
        nupkg_files = glob.glob(os.path.join(pkg_out_dir, "*.nupkg"))
        if not nupkg_files:
            print("Error: No .nupkg file generated.", flush=True)
        else:
            # Get the most recently modified or highest version .nupkg
            nupkg_files.sort(key=os.path.getmtime, reverse=True)
            nupkg_path = nupkg_files[0]
            print(f"Running UiPath Robot with '{robot_path}' on '{nupkg_path}'...")
            result = subprocess.run([robot_path, "execute", "--file", nupkg_path], capture_output=True, text=True, timeout=600)
            
            print("="*40)
            print("UiPath Exit Code:", result.returncode)
            print("UiPath STDOUT:")
            print(result.stdout)
            print("UiPath STDERR:")
            print(result.stderr)
            print("="*40)
    except Exception as e:
        print(f"Error during execution: {e}")
    finally:
        print("========================================")
        print("Terminating FastAPI server and Ngrok...")
        server_process.terminate()
        server_process.wait()
        if 'ngrok_process' in locals():
            ngrok_process.terminate()
            ngrok_process.wait()

if __name__ == "__main__":
    main()
