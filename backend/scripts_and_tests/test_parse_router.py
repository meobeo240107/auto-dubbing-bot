import json

data = json.load(open("douyin_script_data.json", encoding="utf-8"))
print("Top keys:", data.keys())

loader = data.get("loaderData", {})
print("Loader keys:", loader.keys())

for k, v in loader.items():
    if v and isinstance(v, dict):
        print(f"\n--- {k} keys: ---", v.keys())
        for subk, subv in v.items():
            if isinstance(subv, dict):
                print(f"  sub dict: {subk} ->", list(subv.keys())[:10])
            elif isinstance(subv, (list, str, int, bool)):
                print(f"  {subk} -> {type(subv)}")
