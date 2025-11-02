import threading
import shutil
import json
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog


class FilePathManager:
    @staticmethod
    def make_unique_name(path):
        if not path.exists():
            return path
        folder = path.parent
        name = path.stem
        ext = path.suffix
        count = 1
        while True:
            new_path = folder / f"{name} ({count}){ext}"
            if not new_path.exists():
                return new_path
            count += 1


class JSONHistoryManager:
    def __init__(self, file_path):
        self.file_path = file_path
    
    def load(self):
        if not self.file_path.exists():
            return []
        with open(self.file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def save(self, data):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


class FileOrganizer:
    def __init__(self, folder, test_mode=True):
        self.folder = Path(folder)
        self.sorted_folder = self.folder / "sorted_folders"
        self.sorted_folder.mkdir(exist_ok=True)
        self.history_file = self.sorted_folder / "history.json"
        self.test_mode = test_mode
        
        self.history_manager = JSONHistoryManager(self.history_file)
        self.history = self.history_manager.load()

    def get_folder_name(self, ext):
        if not ext:
            return "no_extension"
        ext = ext.lower().replace(".", "")
        if ext == "jpeg":
            return "jpg"
        if ext == "docx":
            return "doc"
        return ext

    def organize(self, stop_event=None):
        moved = []
        files = [f for f in self.folder.iterdir() if f.is_file()]
        
        for file in files:
            if stop_event and stop_event.is_set():
                break
            
            ext = file.suffix
            folder_name = self.get_folder_name(ext)
            target_folder = self.sorted_folder / folder_name
            target_folder.mkdir(exist_ok=True)
            
            new_path = target_folder / file.name
            final_path = FilePathManager.make_unique_name(new_path)
            time = datetime.now().isoformat()
            
            if not self.test_mode:
                shutil.move(str(file), str(final_path))
            
            self.history.append({"from": str(file), "to": str(final_path), "time": time})
            self.history_manager.save(self.history)
            moved.append((str(file), str(final_path)))
        
        return moved

    def undo(self, count=1):
        restored = []
        moves_to_undo = min(count, len(self.history))
        
        for _ in range(moves_to_undo):
            move = self.history.pop()
            original = Path(move["from"])
            current = Path(move["to"])
            
            if current.exists():
                restore_path = FilePathManager.make_unique_name(original)
                shutil.move(str(current), str(restore_path))
                time = datetime.now().isoformat()
                restored.append((str(current), str(restore_path)))
        
        self.history_manager.save(self.history)
        return restored


class UIComponents:
    @staticmethod
    def create_label(parent, text, font_size=10, bold=False, **kwargs):
        font = ("Helvetica", font_size, "bold" if bold else "normal")
        return tk.Label(parent, text=text, font=font, bg="#f6f8fb", **kwargs)
    
    @staticmethod
    def create_button(parent, text, command, bg_color="#6f5af8", **kwargs):
        return tk.Button(parent, text=text, command=command, bg=bg_color, 
                        fg="white", font=("Helvetica", 10), bd=0, 
                        padx=15, pady=8, **kwargs)


class FileOrganizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("File Organizer")
        self.root.geometry("900x600")
        self.root.configure(bg="#f6f8fb")
        
        self.organizer = None
        self.thread = None
        self.stop_event = threading.Event()
        
        self.folder_var = tk.StringVar()
        self.test_var = tk.BooleanVar(value=True)
        
        self.setup_ui()

    def setup_ui(self):
        frame = tk.Frame(self.root, bg="#f6f8fb", padx=20, pady=20)
        frame.pack(fill="both", expand=True)
        
        self.create_folder_section(frame)
        self.create_test_mode_section(frame)
        self.create_button_section(frame)
        self.create_log_section(frame)

    def create_folder_section(self, parent):
        UIComponents.create_label(parent, "Select Folder", 12, True).pack(anchor="w", pady=(0, 5))
        
        folder_frame = tk.Frame(parent, bg="#f6f8fb")
        folder_frame.pack(fill="x", pady=(0, 10))
        
        tk.Entry(folder_frame, textvariable=self.folder_var, font=("Helvetica", 10),
                width=60).pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        UIComponents.create_button(folder_frame, "Browse", self.browse_folder).pack(side="left")

    def create_test_mode_section(self, parent):
        tk.Checkbutton(parent, text="Test mode (preview only)", variable=self.test_var,
                      bg="#f6f8fb", font=("Helvetica", 10)).pack(anchor="w", pady=(0, 15))

    def create_button_section(self, parent):
        btn_frame = tk.Frame(parent, bg="#f6f8fb")
        btn_frame.pack(fill="x", pady=(0, 15))
        
        self.start_btn = UIComponents.create_button(btn_frame, "▶ Start", self.start)
        self.start_btn.pack(side="left", padx=(0, 10))
        
        self.stop_btn = UIComponents.create_button(btn_frame, "⏸ Stop", self.stop, 
                                                   bg_color="#6b7280", state="disabled")
        self.stop_btn.pack(side="left", padx=(0, 10))
        
        UIComponents.create_button(btn_frame, "↩ Undo", self.undo, 
                                  bg_color="#3fb36f").pack(side="left")

    def create_log_section(self, parent):
        UIComponents.create_label(parent, "Activity Log").pack(anchor="w", pady=(0, 5))
        
        self.log = tk.Text(parent, height=20, wrap="word", bg="#0f1113", fg="#9ef6d8",
                          font=("Helvetica", 9), bd=0, padx=10, pady=8)
        self.log.pack(fill="both", expand=True)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_var.set(folder)

    def log_msg(self, msg):
        time = datetime.now().strftime("%H:%M:%S")
        self.log.insert("end", f"[{time}] {msg}\n")
        self.log.see("end")

    def validate_folder(self):
        folder = self.folder_var.get().strip()
        if not folder:
            messagebox.showwarning("Warning", "Please select a folder")
            return None
        
        if not Path(folder).exists():
            messagebox.showerror("Error", "Folder doesn't exist")
            return None
        
        return folder

    def start(self):
        folder = self.validate_folder()
        if not folder:
            return
        
        self.organizer = FileOrganizer(folder, self.test_var.get())
        self.stop_event.clear()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        
        mode = "TEST MODE" if self.test_var.get() else "REAL MODE"
        self.log_msg(f"Starting ({mode}): {folder}")
        
        self.thread = threading.Thread(target=self.run_organize, daemon=True)
        self.thread.start()

    def run_organize(self):
        try:
            moved = self.organizer.organize(self.stop_event)
            
            for from_path, to_path in moved:
                if self.stop_event.is_set():
                    break
                self.log_msg(f"Moved: {Path(from_path).name} → {Path(to_path).parent.name}/{Path(to_path).name}")
            
            if self.test_var.get():
                self.log_msg(f"Test done. {len(moved)} files would be moved")
            else:
                self.log_msg(f"Done! {len(moved)} files moved")
        
        except Exception as e:
            self.log_msg(f"Error: {e}")
        
        finally:
            self.root.after(0, lambda: [
                self.start_btn.config(state="normal"),
                self.stop_btn.config(state="disabled")
            ])

    def stop(self):
        if messagebox.askyesno("Stop", "Stop organizing?"):
            self.stop_event.set()
            self.log_msg("Stopping...")

    def undo(self):
        folder = self.validate_folder()
        if not folder:
            return
        
        if not self.organizer or str(self.organizer.folder) != folder:
            self.organizer = FileOrganizer(folder, True)
        
        count = simpledialog.askinteger("Undo", "How many moves to undo?", 
                                       initialvalue=1, minvalue=1)
        if count is None:
            return
        
        try:
            restored = self.organizer.undo(count)
            if restored:
                for from_path, to_path in restored:
                    self.log_msg(f"Restored: {Path(from_path).name} → {Path(to_path).name}")
                messagebox.showinfo("Success", f"{len(restored)} file(s) restored")
            else:
                messagebox.showinfo("Info", "Nothing to undo")
        except Exception as e:
            messagebox.showerror("Error", f"Undo failed: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = FileOrganizerApp(root)
    root.mainloop()