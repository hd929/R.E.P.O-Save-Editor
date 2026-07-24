import sys, json, re, shutil, requests, webbrowser
from customtkinter import *
from tkinter import BOTH, Text, filedialog, messagebox
from lib.CTkMenuBar import *
from lib.CTkToolTip import *
from lib.decrypt import decrypt_es3
from lib.encrypt import encrypt_es3
from datetime import datetime
from PIL import Image
from pathlib import Path
from threading import Thread

DEBUGLEVEL = None
ES3_KEY = "Why would you want to cheat?... :o It's no fun. :') :'D"

if DEBUGLEVEL:
    import logging
    logging.basicConfig(level=DEBUGLEVEL)
    ui_logger = logging.getLogger("customtkinter")
    ui_logger.setLevel(DEBUGLEVEL)
    logger = logging.getLogger(__name__)
    logger.setLevel(DEBUGLEVEL)

BUNDLE_DIR = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))

CACHE_DIR = Path.home() / ".cache" / "noedl.xyz"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

version = "1.1.0"
json_data = {}
savefilename = ""
savefile_path = None
savefile_dir = Path.home() / "AppData" / "LocalLow" / "semiwork" / "Repo" / "saves"

# ── Colors ──
BG_DARK    = "#1a1a2e"
BG_CARD    = "#16213e"
BG_ENTRY   = "#0f3460"
BG_ACCENT  = "#e94560"
BG_HOVER   = "#533483"
BG_SURFACE = "#222244"
TEXT_DIM   = "#8888aa"
TEXT_LIGHT = "#e0e0ff"
BORDER_CLR = "#333366"

# ── Root ──
root = CTk()
root.geometry("960x600")
root.title("R.E.P.O Save Editor")
try:
    root.iconbitmap(str(BUNDLE_DIR / "icon.ico"))
except Exception:
    pass
root.configure(fg_color=BG_DARK)
set_appearance_mode("dark")
set_default_color_theme("dark-blue")

font_heading = ("Segoe UI", 18, "bold")
font_normal  = ("Segoe UI", 12)
font_small   = ("Segoe UI", 10)
font_mono    = ("Consolas", 10)

# ── Menu bar ──
menu = CTkTitleMenu(master=root)
button_file = menu.add_cascade("File")
button_help = menu.add_cascade("Help")
dropdown1 = CustomDropdownMenu(widget=button_file)
dropdown1.add_option(option="Open", command=lambda: open_file())
dropdown1.add_option(option="Save", command=lambda: save_data())
dropdown2 = CustomDropdownMenu(widget=button_help)
dropdown2.add_option(option="How to Use", command=lambda: webbrowser.open("https://github.com/N0edL/R.E.P.O-Save-Editor#how-to-use"))
dropdown2.add_option(option="About", command=lambda: webbrowser.open("https://github.com/N0edL/R.E.P.O-Save-Editor"))
dropdown2.add_option(option="Report Issue", command=lambda: webbrowser.open("https://github.com/N0edL/R.E.P.O-Save-Editor/issues/new"))

# ── Footer (version check in background) ──
label_footer = CTkLabel(root, text=f"v{version}  |  {datetime.now().year} noedl.xyz", font=font_small, text_color=TEXT_DIM)
label_footer.pack(side="bottom", pady=5)

def check_version_async():
    try:
        response = requests.get("https://api.github.com/repos/N0edL/R.E.P.O-Save-Editor/releases/latest", timeout=5)
        latest = response.json().get("tag_name", "Unknown")
        if latest not in (version, f"v{version}", "Unknown"):
            root.after(0, lambda: label_footer.configure(
                text=f"v{version}  (Latest: {latest})  |  {datetime.now().year} noedl.xyz"))
    except Exception:
        pass

Thread(target=check_version_async, daemon=True).start()

# ── State ──
players = []
player_entries = {}  # key: "{name}" for health, "{name}_{upgradeKey}" for upgrades

# ── Helpers ──
def decrypt_save(path):
    return json.loads(decrypt_es3(str(path), ES3_KEY))

def create_entry(label_text, parent, update_callback=None, tooltip=None, fg=BG_CARD):
    frame = CTkFrame(parent, fg_color=fg, corner_radius=6)
    frame.pack(fill="x", pady=2, padx=5)
    CTkLabel(frame, text=label_text, font=font_normal, text_color=TEXT_LIGHT).pack(side="left", padx=8)
    entry = CTkEntry(frame, font=font_normal, width=120, border_color=BORDER_CLR, fg_color=BG_ENTRY, text_color="white", corner_radius=6)
    entry.pack(side="right", padx=8, pady=4)
    if tooltip:
        CTkToolTip(frame, tooltip)
    if update_callback:
        entry.bind("<KeyRelease>", update_callback)
    return entry

# ── JSON Highlight ──
def highlight_json():
    textbox.tag_remove("key", "1.0", "end")
    textbox.tag_remove("string", "1.0", "end")
    textbox.tag_remove("number", "1.0", "end")
    textbox.tag_remove("boolean", "1.0", "end")
    json_text = textbox.get("1.0", "end-1c")
    for match in re.finditer(r'(\"[^\"]*\")\s*:', json_text):
        textbox.tag_add("key", f"1.0+{match.start()}c", f"1.0+{match.end(1)}c")
    for match in re.finditer(r'(:\s*)(\"(?:\\.|[^\"\\])*\")', json_text):
        textbox.tag_add("string", f"1.0+{match.start(2)}c", f"1.0+{match.end(2)}c")
    for match in re.finditer(r'(:\s*)(\d+(\.\d+)?)', json_text):
        textbox.tag_add("number", f"1.0+{match.start(2)}c", f"1.0+{match.end(2)}c")
    for match in re.finditer(r'(:\s*)(true|false|null)', json_text):
        textbox.tag_add("boolean", f"1.0+{match.start(2)}c", f"1.0+{match.end(2)}c")

UPGRADE_KEYS = [
    ("Health", "playerUpgradeHealth"),
    ("Stamina", "playerUpgradeStamina"),
    ("Extra Jump", "playerUpgradeExtraJump"),
    ("Launch", "playerUpgradeLaunch"),
    ("Map Player Count", "playerUpgradeMapPlayerCount"),
    ("Speed", "playerUpgradeSpeed"),
    ("Strength", "playerUpgradeStrength"),
    ("Range", "playerUpgradeRange"),
    ("Throw", "playerUpgradeThrow"),
    ("Crown (0 or 1)", "playerHasCrown"),
]

# ── Data sync ──
def update_json_data(event):
    try:
        dd = json_data['dictionaryOfDictionaries']['value']
        dd['runStats']['level'] = int(entry_level.get())
        dd['runStats']['currency'] = int(entry_currency.get())
        dd['runStats']['lives'] = int(entry_lives.get())
        dd['runStats']['chargingStationCharge'] = int(entry_charging.get())
        dd['runStats']['totalHaul'] = int(entry_haul.get())
        json_data['teamName']['value'] = entry_teamname.get()
        for player in players:
            pid = player['id']
            # Health
            health_key = player['name']
            if health_key in player_entries:
                val = int(player_entries[health_key].get())
                player['health'] = val
                dd['playerHealth'][pid] = val
            # Upgrades
            for _, upgrade_key in UPGRADE_KEYS:
                entry_key = f"{player['name']}_{upgrade_key}"
                if entry_key in player_entries:
                    if upgrade_key not in dd:
                        dd[upgrade_key] = {}
                    dd[upgrade_key][pid] = int(player_entries[entry_key].get())
        textbox.delete("1.0", "end")
        textbox.insert("1.0", json.dumps(json_data, indent=4))
        highlight_json()
    except (ValueError, KeyError):
        pass

def on_json_edit(event):
    global json_data
    try:
        updated_data = json.loads(textbox.get("1.0", "end-1c"))
        run = updated_data['dictionaryOfDictionaries']['value']['runStats']
        entry_level.delete(0, "end"); entry_level.insert(0, run['level'])
        entry_currency.delete(0, "end"); entry_currency.insert(0, run['currency'])
        entry_lives.delete(0, "end"); entry_lives.insert(0, run['lives'])
        entry_charging.delete(0, "end"); entry_charging.insert(0, run['chargingStationCharge'])
        entry_haul.delete(0, "end"); entry_haul.insert(0, run['totalHaul'])
        entry_teamname.delete(0, "end"); entry_teamname.insert(0, updated_data['teamName']['value'])
        json_data = updated_data
        highlight_json()
    except (json.JSONDecodeError, KeyError):
        pass

# ── File operations ──
def open_file():
    global json_data, savefilename, savefile_path
    file_path = filedialog.askopenfilename(initialdir=savefile_dir, filetypes=[("Game Save (.es3 file)", "*.es3")])
    if not file_path:
        return
    try:
        json_data = decrypt_save(file_path)
        savefilename = Path(file_path).name
        savefile_path = Path(file_path)
        update_ui_from_json(json_data)
    except Exception as e:
        messagebox.showerror("Open Error", f"Failed to open:\n{file_path}\n\n{e}")

def save_data():
    if not json_data:
        messagebox.showerror("Error", "No data to save.")
        return
    if not savefile_path:
        messagebox.showerror("Error", "No save file loaded.")
        return
    try:
        encrypted_data = encrypt_es3(json.dumps(json_data, indent=4).encode('utf-8'), ES3_KEY)
        with open(savefile_path, 'wb') as f:
            f.write(encrypted_data)
        messagebox.showinfo("Saved", f"Saved:\n{savefile_path.name}")
    except Exception as e:
        messagebox.showerror("Save Error", f"Failed to save:\n{e}")

# ── Steam avatar ──
def fetch_steam_profile_picture(player_id):
    cached_image_path = CACHE_DIR / f"{player_id}.png"
    if cached_image_path.exists():
        return str(cached_image_path)
    url = f"https://steamcommunity.com/profiles/{player_id}?xml=1"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            match = re.search(r'<avatarIcon><!\[CDATA\[(.*?)\]\]></avatarIcon>', response.text)
            if match:
                img_url = match.group(1)
                if img_url.startswith("http"):
                    img_data = requests.get(img_url, timeout=5).content
                    with open(cached_image_path, 'wb') as file:
                        file.write(img_data)
                    return str(cached_image_path)
    except Exception:
        pass
    fallback_path = CACHE_DIR / f"{player_id}_fallback.png"
    if not fallback_path.exists():
        src = BUNDLE_DIR / "example.png"
        if src.exists():
            shutil.copy(str(src), str(fallback_path))
        else:
            return None
    return str(fallback_path)

# ── Editor UI ──
def update_ui_from_json(data):
    global players, player_entries
    players.clear()
    player_entries.clear()

    # Clear root content
    for w in root.winfo_children():
        if w != label_footer and w != menu:
            w.destroy()

    # ── Toolbar ──
    toolbar = CTkFrame(root, fg_color=BG_SURFACE, corner_radius=0, height=45)
    toolbar.pack(fill="x", padx=10, pady=(5, 0))
    toolbar.pack_propagate(False)

    CTkButton(toolbar, text="Back", font=font_normal, width=70, height=32,
              fg_color=BG_ENTRY, hover_color=BG_HOVER, corner_radius=6,
              command=show_save_picker).pack(side="left", padx=8, pady=6)

    CTkLabel(toolbar, text=savefilename, font=font_normal, text_color=TEXT_DIM).pack(side="left", padx=5)

    CTkButton(toolbar, text="Save", font=("Segoe UI", 13, "bold"), width=90, height=32,
              fg_color=BG_ACCENT, hover_color="#c23152", corner_radius=6,
              command=save_data).pack(side="right", padx=8, pady=6)

    tabview = CTkTabview(root, width=680, height=400, fg_color=BG_DARK,
                         segmented_button_fg_color=BG_SURFACE,
                         segmented_button_selected_color=BG_ACCENT,
                         segmented_button_selected_hover_color=BG_HOVER,
                         segmented_button_unselected_color=BG_SURFACE,
                         segmented_button_unselected_hover_color=BG_HOVER)
    tabview.pack(fill=BOTH, expand=True, padx=10, pady=(5, 0))
    tabview.add("World")
    tabview.add("Player")
    tabview.add("Advanced")

    # ── World tab ──
    frame_world = CTkScrollableFrame(tabview.tab("World"), fg_color="transparent")
    frame_world.pack(fill=BOTH, expand=True, padx=5, pady=5)

    section_run = CTkFrame(frame_world, fg_color=BG_SURFACE, corner_radius=10)
    section_run.pack(fill="x", pady=(0, 8))
    CTkLabel(section_run, text="Run Stats", font=font_heading, text_color=BG_ACCENT).pack(anchor="w", padx=12, pady=(8, 4))

    global entry_level, entry_currency, entry_lives, entry_charging, entry_haul, entry_teamname
    entry_level = create_entry("Level", section_run, update_json_data, "Current game level", fg=BG_SURFACE)
    entry_currency = create_entry("Currency", section_run, update_json_data, "Currency (in thousands)", fg=BG_SURFACE)
    entry_lives = create_entry("Lives", section_run, update_json_data, "Number of lives", fg=BG_SURFACE)
    entry_charging = create_entry("Charging Station", section_run, update_json_data, "Charging station charge amount", fg=BG_SURFACE)
    entry_haul = create_entry("Total Haul", section_run, update_json_data, "Total haul value", fg=BG_SURFACE)

    run = data.get('dictionaryOfDictionaries', {}).get('value', {}).get('runStats', {})
    entry_level.insert(0, run.get('level', 1))
    entry_currency.insert(0, run.get('currency', 0))
    entry_lives.insert(0, run.get('lives', 3))
    entry_charging.insert(0, run.get('chargingStationCharge', 0))
    entry_haul.insert(0, run.get('totalHaul', 0))

    # Tools section
    section_tools = CTkFrame(frame_world, fg_color=BG_SURFACE, corner_radius=10)
    section_tools.pack(fill="x", pady=(0, 8))
    CTkLabel(section_tools, text="Quick Actions", font=font_heading, text_color=BG_ACCENT).pack(anchor="w", padx=12, pady=(8, 4))
    
    def recharge_all_items():
        if 'itemStatBattery' in json_data['dictionaryOfDictionaries']['value']:
            count = 0
            for item_key in json_data['dictionaryOfDictionaries']['value']['itemStatBattery']:
                if json_data['dictionaryOfDictionaries']['value']['itemStatBattery'][item_key] != 100:
                    json_data['dictionaryOfDictionaries']['value']['itemStatBattery'][item_key] = 100
                    count += 1
            if count > 0:
                textbox.delete("1.0", "end")
                textbox.insert("1.0", json.dumps(json_data, indent=4))
                highlight_json()
                messagebox.showinfo("Success", f"Recharged {count} items (Guns, Crystals, etc.) to 100%!")
            else:
                messagebox.showinfo("Info", "All items are already fully charged.")

    btn_recharge = CTkButton(section_tools, text="⚡ Recharge All Items (100%)", command=recharge_all_items, fg_color=BG_ACCENT, hover_color="#2b7e61", text_color="white")
    btn_recharge.pack(anchor="w", padx=12, pady=(0, 12))

    section_team = CTkFrame(frame_world, fg_color=BG_SURFACE, corner_radius=10)
    section_team.pack(fill="x", pady=(0, 8))
    CTkLabel(section_team, text="Team", font=font_heading, text_color=BG_ACCENT).pack(anchor="w", padx=12, pady=(8, 4))
    entry_teamname = create_entry("Team Name", section_team, update_json_data, "Name of the team", fg=BG_SURFACE)
    entry_teamname.insert(0, data.get('teamName', {}).get('value', 'Unknown'))

    # ── Player tab ──
    frame_player = CTkScrollableFrame(tabview.tab("Player"), fg_color="transparent")
    frame_player.pack(fill=BOTH, expand=True, padx=5, pady=5)

    for player_id, player_name in data.get("playerNames", {}).get("value", {}).items():
        player_health = data.get("dictionaryOfDictionaries", {}).get("value", {}).get("playerHealth", {}).get(player_id, 100)
        players.append({"id": player_id, "name": player_name, "health": player_health})

    for player in players:
        card = CTkFrame(frame_player, corner_radius=10, fg_color=BG_SURFACE, border_width=1, border_color=BORDER_CLR)
        card.pack(fill="x", pady=5)

        header = CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 5))

        pic_path = fetch_steam_profile_picture(player['id'])
        if pic_path:
            try:
                image = Image.open(pic_path)
                my_image = CTkImage(light_image=image, dark_image=image, size=(36, 36))
                CTkLabel(header, image=my_image, text="").pack(side="left", padx=(0, 8))
            except Exception:
                pass

        CTkLabel(header, text=player['name'], font=("Segoe UI", 14, "bold"), text_color="white").pack(side="left")

        health_entry = create_entry("Health", card, update_json_data, "Player health (max 200)", fg=BG_SURFACE)
        health_entry.insert(0, player['health'])
        player_entries[player['name']] = health_entry

        CTkFrame(card, height=1, fg_color=BORDER_CLR).pack(fill="x", padx=10, pady=6)
        CTkLabel(card, text="Upgrades", font=("Segoe UI", 11, "bold"), text_color=TEXT_DIM).pack(anchor="w", padx=14)

        dd = data.get('dictionaryOfDictionaries', {}).get('value', {})
        for label_text, key in UPGRADE_KEYS:
            val = dd.get(key, {}).get(player['id'], 0)
            e = create_entry(label_text, card, update_json_data, fg=BG_SURFACE)
            e.insert(0, val)
            player_entries[f"{player['name']}_{key}"] = e

    # ── Advanced tab ──
    frame_advanced = CTkFrame(tabview.tab("Advanced"), corner_radius=10, fg_color=BG_SURFACE)
    frame_advanced.pack(fill=BOTH, expand=True, padx=5, pady=5)
    CTkLabel(frame_advanced, text="JSON Editor", font=font_heading, text_color=BG_ACCENT).pack(anchor="w", padx=12, pady=(8, 4))

    global textbox
    textbox = Text(frame_advanced, font=font_mono, height=12, wrap="word",
                   bg="#0a0a1a", fg="#e0e0ff", bd=0, highlightthickness=0,
                   insertbackground="white", selectbackground=BG_ACCENT, padx=8, pady=8)
    textbox.pack(fill=BOTH, expand=True, padx=8, pady=(0, 8))
    textbox.insert("1.0", json.dumps(json_data, indent=4))

    textbox.tag_configure("key", foreground="#e94560")
    textbox.tag_configure("string", foreground="#7ac379")
    textbox.tag_configure("number", foreground="#e9c46a")
    textbox.tag_configure("boolean", foreground="#4cc9f0")

    highlight_json()
    textbox.bind("<KeyRelease>", on_json_edit)

# ── Save Picker ──
def get_save_folders():
    """Return list of (folder_path, main_es3_path) sorted by newest first."""
    if not savefile_dir.exists():
        return []
    result = []
    for d in sorted(savefile_dir.iterdir(), reverse=True):
        if d.is_dir() and d.name != "backups":
            es3_files = [f for f in d.glob("*.es3") if "_BACKUP" not in f.name]
            if es3_files:
                latest = max(es3_files, key=lambda f: f.stat().st_mtime)
                result.append((d, latest))
    return result

# Cache for save info to avoid decrypting repeatedly
_save_info_cache = {}

def peek_save_info(es3_path):
    """Read save file and return summary dict, or None on failure. Cached."""
    cache_key = (str(es3_path), es3_path.stat().st_mtime)
    if cache_key in _save_info_cache:
        return _save_info_cache[cache_key]
    try:
        data = decrypt_save(es3_path)
        run = data.get("dictionaryOfDictionaries", {}).get("value", {}).get("runStats", {})
        names = data.get("playerNames", {}).get("value", {})
        team = data.get("teamName", {}).get("value", "?")
        info = {
            "level": run.get("level", "?"),
            "currency": run.get("currency", "?"),
            "lives": run.get("lives", "?"),
            "players": len(names),
            "team": team,
        }
        _save_info_cache[cache_key] = info
        return info
    except Exception:
        _save_info_cache[cache_key] = None
        return None

def show_save_picker():
    # Clear existing content except footer and menu
    for w in root.winfo_children():
        if w != label_footer and w != menu:
            w.destroy()

    if not savefile_dir.exists():
        CTkLabel(root, text=f"Save directory not found:\n{savefile_dir}", font=font_normal,
                 text_color=TEXT_DIM, wraplength=600).pack(expand=True)
        return

    save_folders = get_save_folders()
    if not save_folders:
        CTkLabel(root, text=f"No saves found in:\n{savefile_dir}", font=font_normal,
                 text_color=TEXT_DIM, wraplength=600).pack(expand=True)
        return

    picker_frame = CTkScrollableFrame(root, fg_color="transparent")
    picker_frame.pack(fill=BOTH, expand=True, padx=20, pady=10)

    header = CTkFrame(picker_frame, fg_color="transparent")
    header.pack(fill="x", pady=(0, 12))
    CTkLabel(header, text="Your Saves", font=("Segoe UI", 22, "bold"), text_color="white").pack(side="left")
    CTkLabel(header, text=f"{len(save_folders)} saves found", font=font_small, text_color=TEXT_DIM).pack(side="right")

    def load_save(es3_path):
        global json_data, savefilename, savefile_path
        try:
            json_data = decrypt_save(es3_path)
            savefilename = es3_path.name
            savefile_path = es3_path
            update_ui_from_json(json_data)
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load:\n{es3_path.name}\n\n{e}")

    def duplicate_save(src_folder):
        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        new_name = f"REPO_SAVE_{timestamp}"
        dest_folder = savefile_dir / new_name
        shutil.copytree(str(src_folder), str(dest_folder))
        for f in dest_folder.glob("*.es3"):
            if "_BACKUP" not in f.name:
                f.rename(dest_folder / f"{new_name}.es3")
                break
        messagebox.showinfo("Duplicated", f"Save duplicated as:\n{new_name}")
        show_save_picker()

    def delete_save(src_folder):
        if messagebox.askyesno("Delete Save", f"Delete this save permanently?\n\n{src_folder.name}\n\nThis cannot be undone."):
            shutil.rmtree(str(src_folder))
            show_save_picker()

    for src_folder, es3_path in save_folders:
        mtime = datetime.fromtimestamp(es3_path.stat().st_mtime).strftime("%Y-%m-%d  %H:%M")
        info = peek_save_info(es3_path)

        card = CTkFrame(picker_frame, fg_color=BG_SURFACE, corner_radius=10, border_width=1, border_color=BORDER_CLR)
        card.pack(fill="x", pady=4)

        left = CTkFrame(card, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=14, pady=10)

        CTkLabel(left, text=src_folder.name, font=("Segoe UI", 13, "bold"), text_color="white", anchor="w").pack(anchor="w")
        CTkLabel(left, text=mtime, font=font_small, text_color=TEXT_DIM, anchor="w").pack(anchor="w")

        if info:
            info_text = f"Lv.{info['level']}  |  ${info['currency']}  |  {info['lives']} lives  |  {info['players']} players  |  {info['team']}"
            CTkLabel(left, text=info_text, font=font_small, text_color="#8899bb", anchor="w").pack(anchor="w", pady=(2, 0))

        right = CTkFrame(card, fg_color="transparent")
        right.pack(side="right", padx=10, pady=10)

        CTkButton(right, text="Open", font=font_normal, width=70, height=32,
                  fg_color=BG_ACCENT, hover_color="#c23152", corner_radius=6,
                  command=lambda p=es3_path: load_save(p)).pack(side="left", padx=3)

        CTkButton(right, text="Duplicate", font=font_normal, width=85, height=32,
                  fg_color=BG_ENTRY, hover_color=BG_HOVER, corner_radius=6,
                  command=lambda d=src_folder: duplicate_save(d)).pack(side="left", padx=3)

        CTkButton(right, text="Delete", font=font_normal, width=65, height=32,
                  fg_color="#441122", hover_color="#662233", corner_radius=6,
                  command=lambda d=src_folder: delete_save(d)).pack(side="left", padx=3)

show_save_picker()
root.mainloop()
