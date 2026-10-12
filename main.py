import json
from pathlib import Path

with Path("data/festival.json").open(encoding="utf-8") as file:
    festival = json.load(file)

print(festival["name"])
print(f"From {festival['first_day']} to {festival['last_day']}")
print(
    f"{len(festival['venues'])} venues, "
    f"{len(festival['artists'])} artists, "
    f"{len(festival['performances'])} performances"
)
