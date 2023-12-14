import zipfile
import os
import shutil
import io

def export_zip(folder_path):
    in_memory_zip = io.BytesIO()
    with zipfile.ZipFile(in_memory_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                zipf.write(file_path, arcname)

        # Move the shutil.rmtree outside of the loop
    shutil.rmtree(folder_path)

    in_memory_zip.seek(0)
    zip_bytes = in_memory_zip.read()
    return zip_bytes
