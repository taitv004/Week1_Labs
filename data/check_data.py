import json

with open("/Users/tavantai/Developer/Week1_Labs/data/db.json", "r", encoding="utf-8") as f:
        data = json.load(f)

for i in data:
    print(i)
print("=====================================")
for i in data["orders"][0]:
      print(i)