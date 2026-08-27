import urllib.request
import zipfile
import os

url = "https://github.com/official-stockfish/Stockfish/releases/download/sf_16.1/stockfish-windows-x86-64-avx2.zip"
zip_path = "stockfish.zip"
extract_dir = "real_stockfish"

print("Downloading official Stockfish 16.1 binary from GitHub...")
try:
    urllib.request.urlretrieve(url, zip_path)
    print("Download complete. Extracting...")
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
        
    print(f"Successfully extracted to {os.path.abspath(extract_dir)}")
except Exception as e:
    print(f"Error downloading Stockfish: {e}")
