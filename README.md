<pre>
⠀⠀⠀⠀⠀⠀⠀⠀
  /$$$$$$                      /$$   /$$                     /$$                 /$$                
 /$$__  $$                    | $$$ | $$                    | $$                | $$                
| $$  \__/  /$$$$$$   /$$$$$$ | $$$$| $$ /$$   /$$ /$$   /$$| $$        /$$$$$$ | $$$$$$$   /$$$$$$$
| $$ /$$$$ /$$__  $$ /$$__  $$| $$ $$ $$| $$  | $$|  $$ /$$/| $$       |____  $$| $$__  $$ /$$_____/
| $$|_  $$| $$$$$$$$| $$  \ $$| $$  $$$$| $$  | $$ \  $$$$/ | $$        /$$$$$$$| $$  \ $$|  $$$$$$ 
| $$  \ $$| $$_____/| $$  | $$| $$\  $$$| $$  | $$  >$$  $$ | $$       /$$__  $$| $$  | $$ \____  $$ 
|  $$$$$$/|  $$$$$$$|  $$$$$$/| $$ \  $$|  $$$$$$/ /$$/\  $$| $$$$$$$$|  $$$$$$$| $$$$$$$/ /$$$$$$$/
 \______/  \_______/ \______/ |__/  \__/ \______/ |__/  \__/|________/ \_______/|_______/ |_______/ 
 
                                   Ｐｒｅｄｉｃｔｓ  ｔｏｍｏｒｒｏｗ
                            An initiative by Loa Andersson, Sweden 2025
</pre>

# GeoNuxLabs LM-STAC Downloader  
*An interactive desktop tool for exploring and downloading geospatial datasets from Lantmäteriet’s STAC API*

---

## Overview

GeoNuxLabs STAC Downloader is a modern, map‑driven desktop application for efficiently exploring and downloading geospatial datasets from **Lantmäteriet’s STAC services**.

The application allows you to:

- Paste any STAC search URL  
- Draw a **BBOX** interactively on a map  
- Preview all matching STAC items  
- Download datasets using a robust multi‑threaded engine  
- Track progress in real time  
- Save data to any local directory  

Built with **Python**, **PySide6**, **Leaflet**, and a modular STAC client designed for reliability and performance.

---

## Features

### ✔ STAC-Compatible Search  
- Paste any `/stac-*/v1/search` URL  
- Automatic validation  
- Visual feedback on number of matching items  

### ✔ Interactive BBOX Selection  
- Draw a bounding box directly on a Leaflet map  
- Coordinates automatically injected into the STAC query  
- Real‑time status updates  

### ✔ Tile Preview  
- List all matching STAC items before downloading  
- View metadata such as date, type, and size  
- Avoid unnecessary downloads  

### ✔ Robust Download Engine  
- Multi‑threaded downloads  
- Automatic retry logic  
- Real‑time progress bar  
- Logging of all events  

### ✔ Clean and User-Friendly UI  
- Modern PySide6 interface  
- Clear status messages  
- Dark theme suitable for GIS workflows  
- Optional ASCII splash footer  

---

## Project Structure
```bash
PROJECT_ROOT/
│
├── app.py
├── README.md
│
└── geonuxlabs_stacfetcher/
    ├── main_window.py
    ├── downloader.py
    ├── map_dialog.py
    ├── stac_client.py
    ├── constants.py
    ├── utils.py
    │
    ├── resources/
    │   ├── splash.txt
    │   └── icons/
    │
    └── __init__.py
```

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/geonuxlabs-stac-downloader.git
cd geonuxlabs-stac-downloader
```

### 2. Create a conda environment (recommended)

```bash
conda create -n stacfetcher python=3.11
conda activate stacfetcher
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Running the Application

From the project root:

```bash
python app.py
```

The GUI will launch immediately.

---

## Usage Guide

### 1. Enter a STAC Search URL  
Paste a valid STAC endpoint, for example:

```
/stac-orto/v1/search
```

### 2. Select a Download Folder  
Click **Select folder** and choose where files should be saved.

### 3. Draw a BBOX  
- Click **Open map (draw BBOX)**  
- Draw a rectangle on the map  
- The BBOX is automatically applied to the STAC query  

### 4. Preview Available Tiles  
Click **Preview** to fetch and list all matching STAC items.

### 5. Start Download  
Click **Start download**.  
The progress bar updates in real time.

### 6. Done  
All files are saved to the selected directory.

---

## How It Works

The application uses a structured pipeline to ensure reliable STAC downloads:

- **URL validation** — Ensures the search URL is correctly formatted  
- **BBOX injection** — The drawn polygon is converted to STAC‑compatible coordinates  
- **Preview request** — Fetches all matching STAC items  
- **Download engine**  
  - Multi‑threaded  
  - Retry logic  
  - Progress tracking  
  - Logging  
- **File handling**  
  - Automatic naming  
  - Directory creation  
  - Skips already downloaded files  

---

## Testing

You can test the application with any Lantmäteriet STAC endpoint, such as:

```
/stac-orto/v1/search
/stac-dtm/v1/search
/stac-hm/v1/search
```

---

## Contributing

Contributions are welcome.  
Feel free to open an issue or submit a pull request if you want to:

- Add support for more STAC endpoints  
- Improve UI/UX  
- Enhance the download engine  
- Extend documentation  
- Fix bugs  

---

## License

This project is released under the MIT License.  
You are free to use, modify, and distribute it.
