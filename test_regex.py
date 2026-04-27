import re

err_str = '<function=search_nearest_hospital {"location": "Mumbai-400097"}</function>'

match1 = re.search(r'<function=([a-zA-Z0-9_]+)\s*(\{.*?\})[\s>]*</function>', err_str)
if match1:
    print("Match 1:", match1.groups())
else:
    match2 = re.search(r'<function=([a-zA-Z0-9_]+)>(.*?)</function>', err_str)
    if match2:
        print("Match 2:", match2.groups())
    else:
        print("No match")
