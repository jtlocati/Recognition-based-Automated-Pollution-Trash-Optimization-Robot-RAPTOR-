from datasets import load_dataset
from pathlib import Path

DATASET = load_dataset("keremberke/garbage-object-detection", name="full", trust_remote_code=True)

LABELS = ["biodgradeable", "cardboard", "glass", "metal", "paper", "plastic"]


splits = {"train": "train", "validation": "val", "test": "test"}

path_root = Path("dataset")

for split, YOLOsplit in splits.items():
    if split not in DATASET:
        continue

    img_dir = path_root / "images" / YOLOsplit
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir = path_root / "labels" / YOLOsplit
    lbl_dir.mkdir(parents=True, exist_ok=True)

    for i, row in enumerate(DATASET[split]):
        img = row["image"].convert("RGB")
        width, Height = img.size
        img.save(img_dir / f"{i:06d}.jpg", "JPEG")

        objects = row["objects"]
        lines = []
        
        #COCO formatting converstion
        for bbox, cat in zip(objects["bbox"], objects["category"]):
            x, y, bw, bh = bbox
            xc = (x + bw / 2) / width
            yc = (y + bh / 2) / Height
            lines.append(f"{cat} {xc:.6f} {yc:.6f} {bw/width:.6f} {bh/Height:.6f}")
        (lbl_dir / f"{i:06d}.txt").write_text("\n".join(lines))

    print(f"Wrote {len(DATASET[split])} images => {YOLOsplit}")


#Write => YMAL
yaml_text = f"""path: {path_root.resolve()}
train: images/train
val: images/val
test: images/test

names:
""" 

for i, n in enumerate(LABELS):
    yaml_text += f"  {i}: {n}\n"

Path("data.yaml").write_text(yaml_text)
print("Data Wrote => data.ymal")