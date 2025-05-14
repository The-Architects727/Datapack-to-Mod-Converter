import os
import shutil
import subprocess
import tkinter as tk
from tkinter import filedialog
import openpyxl
import re

class ModConverterApp:
    def __init__(self, master):
        self.master = master
        master.title("Datapack to Fabric Mod Converter")
        master.geometry("400x350")

        self.inputs = [tk.StringVar() for _ in range(3)]  # mod name, description, author
        self.folder_path = tk.StringVar()
        self.dest_path = tk.StringVar()

        labels = ["Mod Name", "Description", "Author"]
        for i, label in enumerate(labels):
            tk.Label(master, text=label).grid(row=i, column=0, sticky="e", padx=5, pady=5)
            tk.Entry(master, textvariable=self.inputs[i], width=40).grid(row=i, column=1, padx=5)

        tk.Button(master, text="Select Datapack Folder", command=self.select_folder).grid(row=3, column=0, columnspan=2)
        tk.Label(master, textvariable=self.folder_path).grid(row=4, column=0, columnspan=2)

        tk.Button(master, text="Select Destination", command=self.select_dest).grid(row=5, column=0, columnspan=2)
        tk.Label(master, textvariable=self.dest_path).grid(row=6, column=0, columnspan=2)

        tk.Button(master, text="Convert", command=self.run_conversion).grid(row=7, column=0, columnspan=2, pady=10)

    def select_folder(self):
        self.folder_path.set(filedialog.askdirectory())

    def select_dest(self):
        self.dest_path.set(filedialog.askdirectory())

    def run_conversion(self):
        mod_name, desc, author = [v.get() for v in self.inputs]
        datapack_src = self.folder_path.get()
        dest_folder = os.path.join(self.dest_path.get(), mod_name.replace(" ", ""))
        modid = mod_name.replace(" ", "").lower()

        template_url = "https://github.com/The-Architects727/SimpleFabricModZip"
        folder_from_repo = "data"

        clone_and_customize(mod_name, desc, modid, author, template_url, datapack_src, dest_folder, folder_from_repo)
        run_versions(dest_folder, modid, mod_name)

def clone_repo(url, path):
    result = subprocess.run(["git", "clone", url, path], capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ Git clone failed:")
        print(result.stderr)
    else:
        print("✅ Git clone successful.")

def copy_folder(src, dst):
    for root, dirs, files in os.walk(src):
        if '.git' in root:
            continue
        rel_path = os.path.relpath(root, src)
        target_dir = os.path.join(dst, rel_path)
        os.makedirs(target_dir, exist_ok=True)
        for file in files:
            shutil.copy2(os.path.join(root, file), os.path.join(target_dir, file))

def replace_in_file(file_path, replacements):
    if not os.path.exists(file_path):
        print(f"⚠️ File not found: {file_path}")
        return
    with open(file_path, 'r') as f:
        text = f.read()
    for old, new in replacements:
        text = text.replace(old, new)
    with open(file_path, 'w') as f:
        f.write(text)

def regex_replace_in_file(file_path, patterns):
    if not os.path.exists(file_path):
        print(f"⚠️ File not found: {file_path}")
        return
    with open(file_path, 'r') as f:
        text = f.read()
    for pattern, repl in patterns:
        text = re.sub(pattern, repl, text)
    with open(file_path, 'w') as f:
        f.write(text)

def replace_line_startswith(file_path, replacements):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        for prefix, new_line in replacements:
            if line.strip().startswith(prefix):
                lines[i] = new_line + '\n'
    with open(file_path, 'w') as f:
        f.writelines(lines)

def rename_structure(dest, mod_name, author):
    old_path = os.path.join(dest, "src", "main", "java", "net", "architects")
    old_file = os.path.join(old_path, "SimpleMod.java")
    new_file = os.path.join(old_path, f"{mod_name}.java")
    if os.path.exists(old_file):
        os.rename(old_file, new_file)

    new_author_path = os.path.join(dest, "src", "main", "java", "net", author)
    if os.path.exists(old_path):
        os.rename(old_path, new_author_path)

def clone_and_customize(name, desc, modid, author, base_url, datapack_path, dest, folder):
    clone_repo(base_url, dest)
    copy_folder(os.path.join(datapack_path, folder), os.path.join(dest, "src/main/resources/data"))

    mod_name_clean = name.replace(" ", "")
    author_clean = author.replace(" ", "")

    replace_in_file(os.path.join(dest, 'src/main/resources/fabric.mod.json'), [
        ('"name": "SimpleMod', f'"name": "{name}'),
        ('This is an example description!', desc),
        ('Me!', author),
        ('net.architects.SimpleMod', f'net.{author_clean}.{mod_name_clean}'),
        ('"id": "simplemod', f'"id": "{modid}')
    ])

    replace_in_file(os.path.join(dest, 'gradle.properties'), [('simplemod', modid)])

    rename_structure(dest, mod_name_clean, author_clean)

    new_java_path = os.path.join(dest, f'src/main/java/net/{author_clean}/{mod_name_clean}.java')
    if os.path.exists(new_java_path):
        replace_in_file(new_java_path, [('simplemod', modid),
                                        ('SimpleMod', mod_name_clean),
                                        ('architects', author)])
    else:
        print(f"⚠️ Java file not found at: {new_java_path}")

def update_java_version(dest_folder, java_version):
    print(f"🔧 Updating Java version to {java_version} in build.gradle files...")

    for root, _, files in os.walk(dest_folder):
        for file in files:
            if file == "build.gradle":
                file_path = os.path.join(root, file)
                print(f"📝 Modifying: {file_path}")
                regex_replace_in_file(file_path, [
                    (r"it\.options\.release\s*=\s*\d+", f"it.options.release = {java_version}"),
                    (r"JavaVersion\.VERSION_\d+", f"JavaVersion.VERSION_{java_version}")
                ])
                print(f"✅ Updated Java version in: {file_path}")

def run_versions(dest, modid, mod_name):
    wb = openpyxl.load_workbook("versions-21.xlsx")
    sheet = wb.active
    failed = []

    for row in sheet.iter_rows(min_row=1, values_only=True):
        mc, mapping, loader, fabric, java_version = row[:5]

        gradle_file = os.path.join(dest, 'gradle.properties')
        fabric_file = os.path.join(dest, 'src/main/resources/fabric.mod.json')

        replace_line_startswith(gradle_file, [
            ("minecraft_version=", f"minecraft_version={mc}"),
            ("yarn_mappings=", f"yarn_mappings={mc}+{mapping}"),
            ("loader_version=", f"loader_version={loader}"),
            ("fabric_version=", f"fabric_version={fabric}+{mc}"),
            ("mod_version=", f"mod_version={mc}-1.0.0")
        ])

        regex_replace_in_file(fabric_file, [
            (r'"minecraft"\s*:\s*"~[^"]+"', f'"minecraft": "~{mc}"')
        ])

        # update_java_version(dest, java_version)

        run_command(dest, 'gradlew build')

        jar_path = os.path.join(dest, "build", "libs", f"{modid}-{mc}.jar")
        if not os.path.exists(jar_path):
            failed.append(mc)

    summary_window = tk.Toplevel()
    tk.Label(summary_window, text=f"Completed for {mod_name}").pack()
    tk.Label(summary_window, text=f"Failed versions: {failed}").pack()

def run_command(folder, cmd):
    print(f"💻 Running command: {cmd} in {folder}")
    result = subprocess.run(cmd, cwd=folder, shell=True, capture_output=True, text=True)
    print("📄 STDOUT:\n", result.stdout)
    print("⚠️ STDERR:\n", result.stderr)

    if result.returncode != 0:
        print(f"❌ Command failed with code {result.returncode}")
    else:
        print("✅ Command completed successfully.")

if __name__ == "__main__":
    root = tk.Tk()
    app = ModConverterApp(root)
    root.mainloop()
