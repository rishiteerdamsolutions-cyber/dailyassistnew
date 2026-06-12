import os
from pathlib import Path
import shutil

slots_dir = Path.home() / "Downloads" / "aha" / "Slots"
if not slots_dir.exists():
    print("No slots dir found")
    exit(0)

for slot in slots_dir.iterdir():
    if slot.is_dir():
        for ftype in ["Texts", "Images", "Videos"]:
            old_path = slot / ftype
            if old_path.exists():
                new_dir = slot / "2026" / "6" / ftype
                new_dir.parent.mkdir(parents=True, exist_ok=True)
                
                # Check if old_path has any files inside before moving
                has_files = any(old_path.iterdir())
                if has_files:
                    # Rename old path to new path
                    print(f"Migrating {old_path} to {new_dir}")
                    if new_dir.exists():
                        # Merge contents
                        for item in old_path.iterdir():
                            shutil.move(str(item), str(new_dir / item.name))
                        shutil.rmtree(old_path)
                    else:
                        shutil.move(str(old_path), str(new_dir))
                else:
                    # Just delete empty old directories
                    shutil.rmtree(old_path)
print("Migration complete")
