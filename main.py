import sys, json, re, shutil, requests, webbrowser, os, tempfile
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

version = "1.1.6"
repo_url = "https://github.com/hd929/R.E.P.O-Save-Editor"
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
button_view = menu.add_cascade("View")
button_help = menu.add_cascade("Help")
dropdown1 = CustomDropdownMenu(widget=button_file, width=190)
dropdown1.add_option(option="Open...                 Ctrl+O", command=lambda: open_file())
dropdown1.add_option(option="Save                      Ctrl+S", command=lambda: save_data())
dropdown1.add_option(option="Save As...", command=lambda: save_as())
dropdown1.add_separator()
dropdown1.add_option(option="Create Backup", command=lambda: create_backup())
dropdown1.add_option(option="Import JSON...", command=lambda: import_json())
dropdown1.add_option(option="Export JSON...", command=lambda: export_json())
dropdown1.add_separator()
dropdown1.add_option(option="Open Save Folder", command=lambda: open_save_folder())
dropdown1.add_option(option="Exit", command=root.destroy)
dropdown_view = CustomDropdownMenu(widget=button_view, width=170)
dropdown_view.add_option(option="Save Picker", command=lambda: show_save_picker())
dropdown_view.add_option(option="Reload Save             F5", command=lambda: reload_save())
dropdown_view.add_option(option="Refresh Preview", command=lambda: refresh_save_picker())
dropdown2 = CustomDropdownMenu(widget=button_help)
dropdown2.add_option(option="How to Use", command=lambda: webbrowser.open(f"{repo_url}#how-to-use"))
dropdown2.add_option(option="About", command=lambda: webbrowser.open(repo_url))
dropdown2.add_option(option="Report Issue", command=lambda: webbrowser.open(f"{repo_url}/issues/new"))

# ── Footer (version check in background) ──
label_footer = CTkLabel(root, text=f"v{version}  |  {datetime.now().year} noedl.xyz", font=font_small, text_color=TEXT_DIM)
label_footer.pack(side="bottom", pady=5)

def check_version_async():
    try:
        response = requests.get(f"{repo_url}/releases/latest", timeout=5)
        latest = response.json().get("tag_name", "Unknown")
        if latest not in (version, f"v{version}", "Unknown"):
            root.after(0, lambda: label_footer.configure(
                text=f"v{version}  (Latest: {latest})  |  {datetime.now().year}"))
    except Exception:
        pass

Thread(target=check_version_async, daemon=True).start()
root.bind_all("<Control-o>", lambda event: open_file())
root.bind_all("<Control-s>", lambda event: save_data())
root.bind_all("<F5>", lambda event: reload_save())

# ── State ──
players = []
player_entries = {}  # key: steam_id for health, steam_id + "_" + upgradeKey for upgrades

# ── Helpers ──
def decrypt_save(path):
    return json.loads(decrypt_es3(str(path), ES3_KEY))

_pending_data_update = None
_pending_json_edit = None

def schedule_data_update(event=None):
    global _pending_data_update
    if _pending_data_update:
        root.after_cancel(_pending_data_update)
    _pending_data_update = root.after(180, update_json_data)

def schedule_json_edit(event=None):
    global _pending_json_edit
    if _pending_json_edit:
        root.after_cancel(_pending_json_edit)
    _pending_json_edit = root.after(250, on_json_edit)

def create_entry(label_text, parent, update_callback=None, tooltip=None, fg=BG_CARD):
    frame = CTkFrame(parent, fg_color=fg, corner_radius=6)
    frame.pack(fill="x", pady=2, padx=5)
    CTkLabel(frame, text=label_text, font=font_normal, text_color=TEXT_LIGHT).pack(side="left", padx=8)
    entry = CTkEntry(frame, font=font_normal, width=120, border_color=BORDER_CLR, fg_color=BG_ENTRY, text_color="white", corner_radius=6)
    entry.pack(side="right", padx=8, pady=4)
    if tooltip:
        CTkToolTip(frame, tooltip)
    if update_callback:
        entry.bind("<KeyRelease>", schedule_data_update)
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
    ("Health", "playerUpgradeHealth", "Item Upgrade Player Health"),
    ("Stamina", "playerUpgradeStamina", "Item Upgrade Player Energy"),
    ("Extra Jump", "playerUpgradeExtraJump", "Item Upgrade Player Extra Jump"),
    ("Launch", "playerUpgradeLaunch", "Item Upgrade Player Tumble Launch"),
    ("Map Player Count", "playerUpgradeMapPlayerCount", "Item Upgrade Map Player Count"),
    ("Speed", "playerUpgradeSpeed", "Item Upgrade Player Sprint Speed"),
    ("Strength", "playerUpgradeStrength", "Item Upgrade Player Grab Strength"),
    ("Range", "playerUpgradeRange", "Item Upgrade Player Grab Range"),
    ("Throw", "playerUpgradeThrow", None),
    ("Crown (0 or 1)", "playerHasCrown", None),
]

# ── Data sync ──
def update_json_data(event=None):
    global _pending_data_update
    _pending_data_update = None
    try:
        dd = json_data.get('dictionaryOfDictionaries', {}).get('value', {})
        runStats = dd.get('runStats', {})
        
        # Safe limits for Unity Int32 to prevent OverflowException
        def safe_int(val_str, max_val=2000000000):
            try:
                v = int(val_str)
                return min(v, max_val)
            except (TypeError, ValueError):
                return 0

        runStats['level'] = safe_int(entry_level.get())
        runStats['currency'] = safe_int(entry_currency.get())
        runStats['lives'] = safe_int(entry_lives.get(), max_val=999)
        runStats['chargingStationCharge'] = safe_int(entry_charging.get())
        runStats['totalHaul'] = safe_int(entry_haul.get(), max_val=100000000) # Game multiplies this sometimes, keep it < 100M
        
        if 'dictionaryOfDictionaries' not in json_data:
            json_data['dictionaryOfDictionaries'] = {'value': dd}
        dd['runStats'] = runStats

        if 'teamName' not in json_data:
            json_data['teamName'] = {}
        json_data['teamName']['value'] = entry_teamname.get()

        if 'playerHealth' not in dd:
            dd['playerHealth'] = {}

        for player in players:
            pid = player['id']
            # Health
            if pid in player_entries:
                val = safe_int(player_entries[pid].get(), max_val=2000000000)
                player['health'] = val
                dd['playerHealth'][pid] = val
            # Upgrades
            for _, upgrade_key, _ in UPGRADE_KEYS:
                entry_key = f"{pid}_{upgrade_key}"
                if entry_key in player_entries:
                    if upgrade_key not in dd:
                        dd[upgrade_key] = {}
                    dd[upgrade_key][pid] = safe_int(player_entries[entry_key].get(), max_val=99999)
                    
        # Synchronize itemsUpgradesPurchased to bypass game validation
        if 'itemsUpgradesPurchased' not in dd:
            dd['itemsUpgradesPurchased'] = {}
        if 'itemsPurchasedTotal' not in dd:
            dd['itemsPurchasedTotal'] = {}
            
        for _, upgrade_key, item_name in UPGRADE_KEYS:
            if item_name and upgrade_key in dd:
                total_purchased = sum(dd[upgrade_key].values())
                dd['itemsUpgradesPurchased'][item_name] = total_purchased
                dd['itemsPurchasedTotal'][item_name] = total_purchased

        textbox.delete("1.0", "end")
        textbox.insert("1.0", json.dumps(json_data, indent=4))
        highlight_json()
    except (ValueError, KeyError, TypeError):
        pass

def on_json_edit(event=None):
    global json_data, _pending_json_edit
    _pending_json_edit = None
    try:
        updated_data = json.loads(textbox.get("1.0", "end-1c"))
        dd = updated_data.get('dictionaryOfDictionaries', {})
        inner = dd.get('value', {}) if isinstance(dd, dict) else {}
        run = inner.get('runStats', {}) if isinstance(inner, dict) else {}
        if isinstance(run, dict):
            entry_level.delete(0, "end"); entry_level.insert(0, run.get('level', 1))
            entry_currency.delete(0, "end"); entry_currency.insert(0, run.get('currency', 0))
            entry_lives.delete(0, "end"); entry_lives.insert(0, run.get('lives', 3))
            entry_charging.delete(0, "end"); entry_charging.insert(0, run.get('chargingStationCharge', 0))
            entry_haul.delete(0, "end"); entry_haul.insert(0, run.get('totalHaul', 0))
        team_data = updated_data.get('teamName', {})
        if isinstance(team_data, dict):
            entry_teamname.delete(0, "end"); entry_teamname.insert(0, team_data.get('value', 'Unknown'))
        else:
            entry_teamname.delete(0, "end")
        json_data = updated_data
        highlight_json()
    except (json.JSONDecodeError, KeyError, TypeError):
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
        import traceback
        traceback.print_exc()
        messagebox.showerror("Open Error", f"Failed to open:\n{file_path}\n\n{e}\n\nType: {type(e).__name__}")

def save_data():
    global _pending_data_update, _pending_json_edit
    if _pending_data_update:
        root.after_cancel(_pending_data_update)
        _pending_data_update = None
        update_json_data()
    if _pending_json_edit:
        root.after_cancel(_pending_json_edit)
        _pending_json_edit = None
        on_json_edit()
    if not json_data:
        messagebox.showerror("Error", "No data to save.")
        return False
    if not savefile_path:
        messagebox.showerror("Error", "No save file loaded.")
        return False
    temp_path = None
    try:
        encrypted_data = encrypt_es3(json.dumps(json_data, indent=4).encode('utf-8'), ES3_KEY)
        with tempfile.NamedTemporaryFile('wb', dir=savefile_path.parent, delete=False) as temp_file:
            temp_file.write(encrypted_data)
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_path = Path(temp_file.name)
        os.replace(temp_path, savefile_path)
        _save_info_cache.clear()
        messagebox.showinfo("Saved", f"Saved:\n{savefile_path.name}")
        return True
    except Exception as e:
        if temp_path:
            temp_path.unlink(missing_ok=True)
        messagebox.showerror("Save Error", f"Failed to save:\n{e}")
        return False

def save_as():
    global savefile_path, savefilename
    if not json_data:
        messagebox.showerror("Error", "No data to save.")
        return
    path = filedialog.asksaveasfilename(initialdir=savefile_path.parent if savefile_path else savefile_dir,
                                        initialfile=savefilename or "REPO_SAVE.es3",
                                        defaultextension=".es3", filetypes=[("Game Save (.es3 file)", "*.es3")])
    if not path:
        return
    old_path, old_name = savefile_path, savefilename
    savefile_path, savefilename = Path(path), Path(path).name
    if not save_data():
        savefile_path, savefilename = old_path, old_name

def create_backup():
    if not savefile_path or not savefile_path.exists():
        messagebox.showerror("Backup Error", "No save file loaded.")
        return
    backup_path = savefile_path.with_name(f"{savefile_path.stem}_BACKUP_{datetime.now():%Y_%m_%d_%H_%M_%S}.es3")
    try:
        shutil.copy2(savefile_path, backup_path)
        messagebox.showinfo("Backup Created", f"Created:\n{backup_path.name}")
    except OSError as e:
        messagebox.showerror("Backup Error", f"Failed to create backup:\n{e}")

REQUIRED_TOP_LEVEL = {"dictionaryOfDictionaries", "playerNames", "teamName"}
REQUIRED_DD_INNER = {"runStats"}

def validate_save_schema(data):
    if not isinstance(data, dict):
        raise ValueError("Root JSON value must be an object.")
    missing = REQUIRED_TOP_LEVEL - data.keys()
    if missing:
        raise ValueError(f"Missing required top-level keys: {', '.join(sorted(missing))}.")
    dd = data.get("dictionaryOfDictionaries")
    if not isinstance(dd, dict):
        raise ValueError("dictionaryOfDictionaries must be an object.")
    inner = dd.get("value")
    if not isinstance(inner, dict):
        raise ValueError("dictionaryOfDictionaries.value must be an object.")
    if not REQUIRED_DD_INNER.issubset(inner.keys()):
        raise ValueError(f"Missing required keys in dictionaryOfDictionaries.value: {', '.join(sorted(REQUIRED_DD_INNER - inner.keys()))}.")
    return True

def import_json():
    global json_data
    path = filedialog.askopenfilename(filetypes=[("JSON file", "*.json")])
    if not path:
        return
    try:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
        validate_save_schema(data)
        json_data = data
        update_ui_from_json(json_data)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        messagebox.showerror("Import Error", f"Failed to import JSON:\n{e}")

def export_json():
    if not json_data:
        messagebox.showerror("Export Error", "No data loaded.")
        return
    path = filedialog.asksaveasfilename(initialfile=f"{Path(savefilename).stem or 'save'}.json",
                                        defaultextension=".json", filetypes=[("JSON file", "*.json")])
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8") as file:
            json.dump(json_data, file, indent=4, ensure_ascii=False)
    except OSError as e:
        messagebox.showerror("Export Error", f"Failed to export JSON:\n{e}")

def open_save_folder():
    path = savefile_path.parent if savefile_path else savefile_dir
    if path.exists():
        os.startfile(path)
    else:
        messagebox.showerror("Folder Error", f"Folder not found:\n{path}")

def reload_save():
    global json_data
    if not savefile_path:
        return
    try:
        json_data = decrypt_save(savefile_path)
        update_ui_from_json(json_data)
    except Exception as e:
        messagebox.showerror("Reload Error", f"Failed to reload save:\n{e}")

def refresh_save_picker():
    _save_info_cache.clear()
    show_save_picker()

# ── Steam avatar ──
def fetch_steam_profile_picture(player_id):
    cached_image_path = CACHE_DIR / f"{player_id}.png"
    if cached_image_path.exists():
        return str(cached_image_path)
    url = f"https://steamcommunity.com/profiles/{player_id}?xml=1"
    fallback_path = CACHE_DIR / f"{player_id}_fallback.png"
    if not fallback_path.exists():
        src = BUNDLE_DIR / "example.png"
        if src.exists():
            shutil.copy(str(src), str(fallback_path))
    Thread(target=_download_steam_avatar, args=(player_id, url, cached_image_path), daemon=True).start()
    return str(fallback_path) if fallback_path.exists() else None

def _download_steam_avatar(player_id, url, cached_image_path):
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
    global players, player_entries, json_data, textbox
    import traceback
    try:
        _update_ui_from_json_impl(data)
    except Exception as e:
        traceback.print_exc()
        messagebox.showerror("Load Error", f"Failed to load UI:\n{e}\n\nType: {type(e).__name__}")

def _update_ui_from_json_impl(data):
    global players, player_entries, json_data, textbox
    players.clear()
    player_entries.clear()
    json_data = data

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

    dd = data.get('dictionaryOfDictionaries', {})
    if isinstance(dd, dict):
        inner = dd.get('value', {})
        if isinstance(inner, dict):
            run = inner.get('runStats', {})
            if isinstance(run, dict):
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
        try:
            dd = json_data.get('dictionaryOfDictionaries', {})
            if not isinstance(dd, dict):
                return
            inner = dd.get('value', {})
            if not isinstance(inner, dict):
                return
            battery = inner.get('itemStatBattery', {})
            if not isinstance(battery, dict):
                return
            count = 0
            for item_key in battery:
                if battery[item_key] != 100:
                    battery[item_key] = 100
                    count += 1
            if count > 0:
                textbox.delete("1.0", "end")
                textbox.insert("1.0", json.dumps(json_data, indent=4))
                highlight_json()
                messagebox.showinfo("Success", f"Recharged {count} items (Guns, Crystals, etc.) to 100%!")
            else:
                messagebox.showinfo("Info", "All items are already fully charged.")
        except Exception:
            pass

    btn_recharge = CTkButton(section_tools, text="⚡ Recharge All Items (100%)", command=recharge_all_items, fg_color=BG_ACCENT, hover_color="#2b7e61", text_color="white")
    btn_recharge.pack(anchor="w", padx=12, pady=(0, 12))

    def spawn_items():
        try:
            dd = json_data.get('dictionaryOfDictionaries', {})
            if not isinstance(dd, dict): return
            inner = dd.get('value', {})
            if not isinstance(inner, dict): return

            # Get known items from save file to let user choose
            known_items = set([
                "Item Cart",
                "Item Drone",
                "Item Duck",
                "Item Extraction",
                "Item Grenade",
                "Item Gun Assault Rifle",
                "Item Gun Handgun", 
                "Item Gun Shotgun", 
                "Item Gun Sniper",
                "Item Health Pack Large", 
                "Item Health Pack Small", 
                "Item Melee",
                "Item Mine",
                "Item Orb",
                "Item Phase",
                "Item Power Crystal", 
                "Item Revive Pack",
                "Item Rubber",
                "Item Upgrade",
                "Item Valuable"
            ])
            if 'itemsPurchasedTotal' in inner:
                known_items.update(inner['itemsPurchasedTotal'].keys())
            
            known_items = sorted([k for k in known_items if isinstance(k, str) and k.startswith("Item ")])

            dialog = CTkToplevel(root)
            dialog.title("Delivery Drop (Shopping Cart)")
            dialog.geometry("400x500")
            dialog.transient(root)
            dialog.grab_set()

            CTkLabel(dialog, text="Select Items to Drop", font=font_heading).pack(pady=(15, 5))
            CTkLabel(dialog, text="Items will arrive in the shopping cart.", text_color=TEXT_DIM).pack(pady=(0, 10))

            scroll = CTkScrollableFrame(dialog, fg_color="transparent")
            scroll.pack(fill="both", expand=True, padx=10, pady=5)

            item_vars = {}
            for item_name in known_items:
                frame = CTkFrame(scroll, fg_color=BG_SURFACE)
                frame.pack(fill="x", pady=2)
                display_name = item_name.replace("Item ", "")
                CTkLabel(frame, text=display_name, text_color="white").pack(side="left", padx=10)
                
                var = StringVar(value="0")
                item_vars[item_name] = var
                entry = CTkEntry(frame, textvariable=var, width=50, justify="center")
                entry.pack(side="right", padx=10, pady=4)

            def apply_spawn():
                items_to_add = {}
                for itm, var in item_vars.items():
                    try:
                        val = int(var.get())
                        if val > 0:
                            items_to_add[itm] = val
                    except ValueError:
                        pass
                
                if not items_to_add:
                    dialog.destroy()
                    return

                if 'itemsPurchased' not in inner: inner['itemsPurchased'] = {}
                if 'itemsPurchasedTotal' not in inner: inner['itemsPurchasedTotal'] = {}
                
                for itm, qty in items_to_add.items():
                    inner['itemsPurchased'][itm] = inner['itemsPurchased'].get(itm, 0) + qty
                    inner['itemsPurchasedTotal'][itm] = inner['itemsPurchasedTotal'].get(itm, 0) + qty

                if not save_data():
                    return

                textbox.delete("1.0", "end")
                textbox.insert("1.0", json.dumps(json_data, indent=4))
                highlight_json()
                
                total_qty = sum(items_to_add.values())
                dialog.destroy()
                messagebox.showinfo("Success", f"Added {total_qty} items to your delivery queue!\nLoad your game to receive the package.")

            CTkButton(dialog, text="Add to Delivery", command=apply_spawn, fg_color=BG_ACCENT, hover_color="#2b7e61").pack(pady=15)

        except Exception as e:
            messagebox.showerror("Error", f"Could not spawn items: {e}")

    btn_spawn = CTkButton(section_tools, text="📦 Drop Delivery (Shopping Cart)", command=spawn_items, fg_color=BG_ACCENT, hover_color="#2b7e61", text_color="white")
    btn_spawn.pack(anchor="w", padx=12, pady=(0, 12))

    section_team = CTkFrame(frame_world, fg_color=BG_SURFACE, corner_radius=10)
    section_team.pack(fill="x", pady=(0, 8))
    CTkLabel(section_team, text="Team", font=font_heading, text_color=BG_ACCENT).pack(anchor="w", padx=12, pady=(8, 4))
    entry_teamname = create_entry("Team Name", section_team, update_json_data, "Name of the team", fg=BG_SURFACE)
    team_name_data = data.get('teamName', {})
    if isinstance(team_name_data, dict):
        entry_teamname.insert(0, team_name_data.get('value', 'Unknown'))
    else:
        entry_teamname.insert(0, str(team_name_data) if team_name_data else 'Unknown')

    # ── Player tab ──
    frame_player = CTkScrollableFrame(tabview.tab("Player"), fg_color="transparent")
    frame_player.pack(fill=BOTH, expand=True, padx=5, pady=5)

    player_names_data = data.get("playerNames", {})
    if isinstance(player_names_data, dict):
        pn_value = player_names_data.get("value", {})
        if isinstance(pn_value, dict):
            for player_id, player_name in pn_value.items():
                dd2 = data.get("dictionaryOfDictionaries", {})
                ph = {}
                if isinstance(dd2, dict):
                    inner2 = dd2.get("value", {})
                    if isinstance(inner2, dict):
                        ph = inner2.get("playerHealth", {})
                        if not isinstance(ph, dict):
                            ph = {}
                players.append({"id": player_id, "name": player_name, "health": ph.get(player_id, 100)})

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
        player_entries[player['id']] = health_entry

        def make_change_id_cmd(old_id):
            def cmd():
                dialog = CTkInputDialog(text="Enter new 17-digit Steam ID:", title="Change Steam ID")
                new_id = dialog.get_input()
                if new_id and new_id.strip() and new_id != old_id:
                    new_id = new_id.strip()
                    if not re.fullmatch(r"\d{17}", new_id):
                        messagebox.showerror("Invalid Steam ID", "Steam ID must contain exactly 17 digits.")
                        return
                    global json_data
                    def replace_id(value):
                        if isinstance(value, dict):
                            return {replace_id(k): replace_id(v) for k, v in value.items()}
                        if isinstance(value, list):
                            return [replace_id(item) for item in value]
                        return new_id if value == old_id else value
                    json_data = replace_id(json_data)
                    update_ui_from_json(json_data)
                    messagebox.showinfo("Success", f"Changed Steam ID to {new_id}")
            return cmd

        btn_change_id = CTkButton(header, text="Change ID", width=80, height=24, font=font_small, 
                                  fg_color=BG_ENTRY, hover_color=BG_HOVER, command=make_change_id_cmd(player['id']))
        btn_change_id.pack(side="right", padx=10)

        CTkFrame(card, height=1, fg_color=BORDER_CLR).pack(fill="x", padx=10, pady=6)
        CTkLabel(card, text="Upgrades", font=("Segoe UI", 11, "bold"), text_color=TEXT_DIM).pack(anchor="w", padx=14)

        dd3 = data.get('dictionaryOfDictionaries', {})
        upg_inner = {}
        if isinstance(dd3, dict):
            upg_inner = dd3.get('value', {})
            if not isinstance(upg_inner, dict):
                upg_inner = {}
        for label_text, key, _ in UPGRADE_KEYS:
            upg_dict = upg_inner.get(key, {})
            if not isinstance(upg_dict, dict):
                upg_dict = {}
            val = upg_dict.get(player['id'], 0)
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
    textbox.bind("<KeyRelease>", schedule_json_edit)

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
    """Read save file and return summary dict, or None on failure. Uses in-memory cache keyed by path+mtime."""
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
            "steam_ids": list(names.keys()) if isinstance(names, dict) else [],
            "player_names": list(names.values()) if isinstance(names, dict) else [],
        }
        _save_info_cache[cache_key] = info
        return info
    except Exception:
        _save_info_cache[cache_key] = None
        return None
def show_save_picker(filter_steam_id=None):
    for w in root.winfo_children():
        if w != label_footer and w != menu:
            w.destroy()

    CTkLabel(root, text="Loading saves...", font=font_normal, text_color=TEXT_DIM).pack(expand=True)
    root.update_idletasks()

    Thread(target=_build_save_picker, args=(filter_steam_id,), daemon=True).start()

def _build_save_picker(filter_steam_id):
    if not savefile_dir.exists():
        root.after(0, _show_no_saves, f"Save directory not found:\n{savefile_dir}")
        return

    save_folders = get_save_folders()
    if not save_folders:
        root.after(0, _show_no_saves, f"No saves found in:\n{savefile_dir}")
        return

    all_steam_ids = {}
    save_infos = {}
    for src_folder, es3_path in save_folders:
        info = peek_save_info(es3_path)
        save_infos[es3_path] = info
        if info and "steam_ids" in info and "player_names" in info:
            for sid, sname in zip(info["steam_ids"], info["player_names"]):
                if sid not in all_steam_ids:
                    all_steam_ids[sid] = sname

    root.after(0, _clear_picker_and_build, filter_steam_id, save_folders, all_steam_ids, save_infos)

def _show_no_saves(message):
    for w in root.winfo_children():
        if w != label_footer and w != menu:
            w.destroy()
    CTkLabel(root, text=message, font=font_normal, text_color=TEXT_DIM, wraplength=600).pack(expand=True)

def _clear_picker_and_build(filter_steam_id, save_folders, all_steam_ids, save_infos):
    for w in root.winfo_children():
        if w != label_footer and w != menu:
            w.destroy()

    picker_frame = CTkScrollableFrame(root, fg_color="transparent")
    picker_frame.pack(fill=BOTH, expand=True, padx=20, pady=10)

    header = CTkFrame(picker_frame, fg_color="transparent")
    header.pack(fill="x", pady=(0, 12))
    CTkLabel(header, text="Your Saves", font=("Segoe UI", 22, "bold"), text_color="white").pack(side="left")

    if all_steam_ids:
        filter_frame = CTkFrame(header, fg_color="transparent")
        filter_frame.pack(side="right", padx=(10, 0))
        CTkLabel(filter_frame, text="Filter by Account:", font=font_small, text_color=TEXT_DIM).pack(side="left", padx=(0, 5))

        filter_options = ["All Accounts"] + [f"{name} ({sid})" for sid, name in all_steam_ids.items()]

        current_val = "All Accounts"
        if filter_steam_id and filter_steam_id in all_steam_ids:
            current_val = f"{all_steam_ids[filter_steam_id]} ({filter_steam_id})"

        def on_filter_change(choice):
            if choice == "All Accounts":
                show_save_picker(None)
            else:
                sid = choice.split(" (")[-1].replace(")", "")
                show_save_picker(sid)

        dropdown = CTkOptionMenu(filter_frame, values=filter_options, command=on_filter_change,
                                 fg_color=BG_ENTRY, button_color=BG_SURFACE, button_hover_color=BG_HOVER,
                                 dropdown_fg_color=BG_SURFACE, dropdown_hover_color=BG_HOVER, width=200)
        dropdown.set(current_val)
        dropdown.pack(side="left")

    filtered_folders = []
    for src_folder, es3_path in save_folders:
        info = save_infos[es3_path]
        if filter_steam_id and info and "steam_ids" in info:
            if filter_steam_id not in info["steam_ids"]:
                continue
        filtered_folders.append((src_folder, es3_path))

    CTkLabel(header, text=f"{len(filtered_folders)} saves found", font=font_small,
             text_color=TEXT_DIM).pack(side="right", padx=(0, 15))

    def load_save(es3_path):
        global json_data, savefilename, savefile_path
        try:
            json_data = decrypt_save(es3_path)
            savefilename = es3_path.name
            savefile_path = es3_path
            update_ui_from_json(json_data)
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Load Error", f"Failed to load:\n{es3_path.name}\n\n{e}\n\nType: {type(e).__name__}")

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
        show_save_picker(filter_steam_id)

    def delete_save(src_folder):
        if messagebox.askyesno("Delete Save", f"Delete this save permanently?\n\n{src_folder.name}\n\nThis cannot be undone."):
            shutil.rmtree(str(src_folder))
            show_save_picker(filter_steam_id)

    for src_folder, es3_path in filtered_folders:
        mtime = datetime.fromtimestamp(es3_path.stat().st_mtime).strftime("%Y-%m-%d  %H:%M")
        info = save_infos[es3_path]

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
