# <img src="./icon.ico" alt="Icon" width="30" style="vertical-align: middle;"> R.E.P.O Save Editor

## Overview

**R.E.P.O Save Editor** is a graphical user interface (GUI) tool designed to edit and manage save files for the game **R.E.P.O**. The tool allows users to modify various game statistics such as currency, player health, lives, upgrades, and other in-game data.

This tool provides a clean, user-friendly dark mode interface for the editing process. It supports Steam profile integration, allowing players' profile pictures to be fetched and displayed automatically.

## Features

- **Auto-detect Saves**: Automatically finds and lists all your R.E.P.O save folders with useful preview info (Level, Currency, Player count).
- **Edit Game Data**: View and modify player stats, world stats, upgrades, and more in a user-friendly interface.
- **Duplicate Saves**: Create game-compatible backups of your save files with one click.
- **Delete Saves**: Clean up old saves directly from the app.
- **Direct Save Overwrite**: Save changes directly to the original file.
- **Advanced JSON Editor**: Built-in syntax-highlighted JSON editor for advanced modifications.
- **Standalone Executable**: No need to install Python or dependencies, just run the `.exe`.

## How to Use  

1. **Download the latest release**:  
   Go to the [Releases page](https://github.com/hd929/R.E.P.O-Save-Editor/releases) and download `REPO_Save_Editor.exe`.  

2. **Run the tool**:  
   Simply double-click `REPO_Save_Editor.exe` to launch the app. No installation required.

3. **Select a save**:  
   The app will automatically scan your R.E.P.O save directory (`AppData/LocalLow/semiwork/Repo/saves`) and list all available saves. Click **Open** on the save you want to edit.

4. **Edit the Data**:  
   Modify values such as player health, upgrades, currency, or team name in the tabs provided.  

5. **Save Changes**:  
   Click the **Save** button in the top right corner. The changes will be applied directly to the `.es3` file.

6. **Duplicate/Backup**:
   It's highly recommended to click **Duplicate** before making major edits or attempting a difficult run in-game to preserve your progress.

## Contributions

Feel free to fork the repository and submit pull requests for any improvements or bug fixes!

---

### For Developers

If you want to build the tool from source:

1. Make sure you have Python 3.8+ installed.
2. Clone the repository.
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the app:
   ```bash
   python main.py
   ```
5. Build the executable (requires PyInstaller):
   ```bash
   pyinstaller --noconfirm --onefile --windowed --icon "icon.ico" --add-data "icon.ico;." --add-data "example.png;." --add-data "lib;lib" --name "REPO_Save_Editor" main.py
   ```
