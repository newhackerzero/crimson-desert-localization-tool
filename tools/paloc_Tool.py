import sys
import os
import json
import struct

def extract_paloc(file_path):
    print(f"[*] Extracting file: {file_path}")
    entries = []
    tail_data = b""
    
    with open(file_path, "rb") as f:
        while True:
            # 1. Read 8-byte marker
            marker = f.read(8)
            if not marker:
                break

            # If less than 8 bytes remain, save as tail data
            if len(marker) < 8:
                tail_data = marker + f.read()
                break
            
            # 2. Read key length (4 bytes)
            k_len_data = f.read(4)
            if len(k_len_data) < 4:
                tail_data = marker + k_len_data + f.read()
                break
            k_len = struct.unpack("<I", k_len_data)[0]
            
            # 3. Read key
            key_bytes = f.read(k_len)
            key_str = key_bytes.decode('utf-8', errors='ignore')
            
            # 4. Read text length (4 bytes)
            v_len_data = f.read(4)
            v_len = struct.unpack("<I", v_len_data)[0]
            
            # 5. Read actual text
            val_bytes = f.read(v_len)
            val_str = val_bytes.decode('utf-8', errors='ignore')
            
            entries.append({
                "marker": marker.hex(),
                "key": key_str,
                "original": val_str,
                "translation": val_str
            })

    # Build JSON structure
    output_data = {
        "metadata": {
            "tail_bytes": tail_data.hex()
        },
        "entries": entries
    }
    
    base = os.path.basename(file_path)
    out_path = base + ".json"
    with open(out_path, "w", encoding="utf-8") as out_f:
        json.dump(output_data, out_f, ensure_ascii=False, indent=4)
        
    print(f"[+] Extraction completed successfully! JSON saved to: {out_path}")
    print(f"[i] Total entries found: {len(entries)}")

def repack_paloc(json_path):
    print(f"[*] Repacking file: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    base = os.path.splitext(os.path.basename(json_path))[0]
    out_path = base + "_repacked.paloc"

    entries = data.get("entries", [])

    with open(out_path, "wb") as f:
        for entry in entries:
            f.write(bytes.fromhex(entry["marker"]))

            key_bytes = entry["key"].encode('utf-8')
            f.write(struct.pack("<I", len(key_bytes)))
            f.write(key_bytes)

            val_bytes = entry["translation"].encode('utf-8')
            f.write(struct.pack("<I", len(val_bytes)))
            f.write(val_bytes)

        tail_hex = data.get("metadata", {}).get("tail_bytes", "")
        if tail_hex:
            f.write(bytes.fromhex(tail_hex))

    print(f"[+] Repacking completed successfully! Output file: {out_path}")

def main():
    if len(sys.argv) < 2:
        print("Usage: paloc_Tool.py <file.paloc | file.json>")
        return

    input_file = sys.argv[1]

    try:
        if input_file.lower().endswith(".json"):
            repack_paloc(input_file)
        else:
            extract_paloc(input_file)
    except Exception as e:
        print(f"[!] Error occurred: {e}")
        
    print("")


if __name__ == "__main__":
    main()